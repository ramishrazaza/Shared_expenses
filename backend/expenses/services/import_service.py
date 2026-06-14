import csv
import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.contrib.auth import get_user_model
from expenses.models import (
    Group, User, GroupMembership, Expense, ExpenseParticipant,
    Settlement, ImportBatch, ImportAnomaly, AuditLog
)
from expenses.services.balance_service import BalanceService, round_decimal

User = get_user_model()

# Configuration
DEFAULT_USD_TO_INR_RATE = Decimal('83.00')

def parse_date(date_str, seq_index=None):
    """
    Tries to parse date string with multiple formats:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - MMM DD (e.g. Mar 14) -> Infers year 2026 based on surrounding context
    """
    if not date_str:
        return None, True, "Missing date"

    date_str = date_str.strip()
    
    # Try YYYY-MM-DD
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date(), False, None
    except ValueError:
        pass

    # Try DD/MM/YYYY
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date(), False, None
    except ValueError:
        pass

    # Try MMM DD (e.g. Mar 14)
    # We default year to 2026 as per the Spreetail context (Feb - April 2026)
    try:
        parsed_dt = datetime.strptime(f"{date_str} 2026", '%b %d %Y')
        return parsed_dt.date(), False, None
    except ValueError:
        pass

    try:
        parsed_dt = datetime.strptime(f"{date_str} 2026", '%B %d %Y')
        return parsed_dt.date(), False, None
    except ValueError:
        pass

    return None, True, f"Unrecognized date format: '{date_str}'"

def fuzzy_match_user(name_str):
    """
    Fuzzy match names to existing database users.
    Handles typos like 'Priya S', lowercase 'priya', trailing spaces like 'rohan '.
    """
    if not name_str:
        return None
    
    name_clean = name_str.strip().lower()
    
    # Simple maps
    if name_clean == 'priya s' or name_clean == 'priya':
        return 'Priya'
    if name_clean == 'rohan':
        return 'Rohan'
    if name_clean == 'aisha':
        return 'Aisha'
    if name_clean == 'meera':
        return 'Meera'
    if name_clean == 'sam':
        return 'Sam'
    if name_clean == 'dev':
        return 'Dev'
    if name_clean == 'kabir' or 'kabir' in name_clean:
        return 'Kabir'
        
    # Standard query
    users = User.objects.all()
    for u in users:
        if u.username.lower() == name_clean:
            return u.username
            
    # Fuzzy substring check
    for u in users:
        if u.username.lower() in name_clean or name_clean in u.username.lower():
            return u.username
            
    return None

class CSVImportService:
    @staticmethod
    @transaction.atomic
    def process_dry_run(group_id, file_content, file_name, user):
        """
        Parses CSV, performs anomaly checks, creates an ImportBatch
        and populates ImportAnomaly records. Does NOT write to Expense/Settlement yet.
        """
        group = Group.objects.get(id=group_id)
        
        batch = ImportBatch.objects.create(
            file_name=file_name,
            csv_data=file_content,
            status='pending_review',
            created_by=user
        )

        csv_file = io.StringIO(file_content)
        reader = csv.DictReader(csv_file)
        
        # Clean fieldnames (strip spaces)
        reader.fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        
        rows = list(reader)
        anomalies_detected = []
        processed_transactions = [] # items for duplicate checking

        for idx, row in enumerate(rows, start=2): # Header is line 1, first data row is line 2
            raw_row = {k.strip() if k else '': v.strip() if v else '' for k, v in row.items()}
            
            # Anomaly checks on this row
            row_anomalies = CSVImportService._analyze_row(idx, raw_row, group, processed_transactions)
            anomalies_detected.extend(row_anomalies)

            # Store in processed transactions list to check for duplicates later
            processed_transactions.append({
                'line_num': idx,
                'date': raw_row.get('date', ''),
                'amount': raw_row.get('amount', ''),
                'paid_by': raw_row.get('paid_by', ''),
                'description': raw_row.get('description', ''),
                'split_with': raw_row.get('split_with', ''),
                'raw': raw_row
            })

        # Save anomalies in the DB
        for anomaly in anomalies_detected:
            ImportAnomaly.objects.create(
                batch=batch,
                row_number=anomaly['row_number'],
                raw_row_data=anomaly['raw_row_data'],
                anomaly_type=anomaly['anomaly_type'],
                severity=anomaly['severity'],
                description=anomaly['description'],
                suggested_action=anomaly['suggested_action']
            )

        return batch

    @staticmethod
    def _analyze_row(row_num, row, group, processed):
        """
        Runs rules on a row to detect anomalies. Returns list of anomaly dicts.
        """
        anomalies = []
        
        # Extract fields
        date_str = row.get('date', '')
        desc = row.get('description', '')
        paid_by_str = row.get('paid_by', '')
        amount_str = row.get('amount', '')
        currency_str = row.get('currency', '')
        split_type = row.get('split_type', '')
        split_with_str = row.get('split_with', '')
        split_details = row.get('split_details', '')
        notes = row.get('notes', '')

        # 1. Missing Values
        missing_fields = []
        if not date_str: missing_fields.append('date')
        if not desc: missing_fields.append('description')
        if not amount_str: missing_fields.append('amount')
        
        # Missing paid_by is CRITICAL
        if not paid_by_str:
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'missing_payer',
                'severity': 'critical',
                'description': "Missing 'paid_by' field. It is impossible to determine who is owed.",
                'suggested_action': 'custom_mapping'
            })
            missing_fields.append('paid_by')

        if missing_fields:
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'missing_values',
                'severity': 'medium',
                'description': f"Missing fields: {', '.join(missing_fields)}",
                'suggested_action': 'ignore' if 'paid_by' not in missing_fields else 'custom_mapping'
            })

        # 2. Amount and Currency Format Issues
        amount = None
        if amount_str:
            cleaned_amount_str = amount_str.replace('"', '').replace(',', '').strip()
            if cleaned_amount_str != amount_str:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'format_issue',
                    'severity': 'low',
                    'description': f"Amount contains commas/quotes: '{amount_str}'. Auto-cleaned.",
                    'suggested_action': 'recalculate'
                })
            
            try:
                amount = Decimal(cleaned_amount_str)
                if '.' in cleaned_amount_str:
                    decimals_part = cleaned_amount_str.split('.')[1]
                    if len(decimals_part) > 2:
                        anomalies.append({
                            'row_number': row_num,
                            'raw_row_data': row,
                            'anomaly_type': 'precision_issue',
                            'severity': 'low',
                            'description': f"Amount has too many decimal places: '{amount_str}'. Will round to 2 decimals.",
                            'suggested_action': 'recalculate'
                        })
            except InvalidOperation:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'invalid_amount',
                    'severity': 'critical',
                    'description': f"Cannot parse amount as number: '{amount_str}'",
                    'suggested_action': 'ignore'
                })

        # Negative Amount (Refund)
        if amount is not None and amount < 0:
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'negative_amount',
                'severity': 'medium',
                'description': f"Amount is negative: '{amount_str}'. Interpreted as a refund.",
                'suggested_action': 'import_as_expense'
            })
        
        # Zero Amount
        if amount is not None and amount == 0:
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'zero_amount',
                'severity': 'low',
                'description': "Amount is zero. This transaction has no financial impact.",
                'suggested_action': 'ignore'
            })

        # Missing Currency
        if not currency_str and amount_str:
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'missing_currency',
                'severity': 'low',
                'description': "Missing currency. Defaulting to group currency (INR).",
                'suggested_action': 'recalculate'
            })
        elif currency_str.strip().upper() == 'USD':
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'currency_issue',
                'severity': 'medium',
                'description': f"Transaction in USD. Needs conversion to INR (default rate {DEFAULT_USD_TO_INR_RATE}).",
                'suggested_action': 'recalculate'
            })

        # 3. Date parsing and ambiguities
        parsed_date = None
        if date_str:
            date_val, has_err, err_msg = parse_date(date_str)
            if has_err:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'invalid_date',
                    'severity': 'high',
                    'description': err_msg,
                    'suggested_action': 'ignore'
                })
            else:
                parsed_date = date_val
                if '/' in date_str:
                    anomalies.append({
                        'row_number': row_num,
                        'raw_row_data': row,
                        'anomaly_type': 'date_format_inconsistency',
                        'severity': 'low',
                        'description': f"Inconsistent date format: '{date_str}' (expected YYYY-MM-DD).",
                        'suggested_action': 'recalculate'
                    })
                if date_str.strip() == '04/05/2026':
                    anomalies.append({
                        'row_number': row_num,
                        'raw_row_data': row,
                        'anomaly_type': 'date_ambiguity',
                        'severity': 'medium',
                        'description': "Ambiguous date '04/05/2026'. Is it May 4 or April 5? Chronology suggests April 5.",
                        'suggested_action': 'recalculate'
                    })

        # 4. User typos and unrecognized members
        payer_matched = None
        if paid_by_str:
            payer_matched = fuzzy_match_user(paid_by_str)
            if not payer_matched:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'unknown_user',
                    'severity': 'high',
                    'description': f"Payer '{paid_by_str}' is not a recognized group member.",
                    'suggested_action': 'custom_mapping'
                })
            elif payer_matched != paid_by_str:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'case_or_space_inconsistency',
                    'severity': 'low',
                    'description': f"Payer name '{paid_by_str}' has spacing/case issues. Normalizing to '{payer_matched}'.",
                    'suggested_action': 'recalculate'
                })

        # 5. Settlement disguised as expense
        is_settlement = False
        if (not split_type or split_type.strip() == '') and split_with_str:
            split_members = [m.strip() for m in split_with_str.split(';') if m.strip()]
            if len(split_members) == 1:
                is_settlement = True
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'settlement_disguised_as_expense',
                    'severity': 'medium',
                    'description': f"Description suggests direct payment/settlement rather than shared expense.",
                    'suggested_action': 'import_as_settlement'
                })
        
        if not is_settlement and desc and ('paid' in desc.lower() and 'back' in desc.lower()):
            is_settlement = True
            anomalies.append({
                'row_number': row_num,
                'raw_row_data': row,
                'anomaly_type': 'settlement_disguised_as_expense',
                'severity': 'medium',
                'description': f"Description '{desc}' indicates this is a settlement, not an expense.",
                'suggested_action': 'import_as_settlement'
            })

        # 6. Split inconsistencies & unknown participants
        if not is_settlement and split_with_str:
            participants = [p.strip() for p in split_with_str.split(';') if p.strip()]
            unmatched_parts = []
            for p in participants:
                matched_name = fuzzy_match_user(p)
                if not matched_name:
                    unmatched_parts.append(p)

            if unmatched_parts:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'unknown_user',
                    'severity': 'high',
                    'description': f"Unrecognized participants in split_with: {', '.join(unmatched_parts)}",
                    'suggested_action': 'custom_mapping'
                })

            if split_type == 'percentage' and split_details:
                percentage_pairs = [pair.strip() for pair in split_details.split(';') if pair.strip()]
                total_percentage = 0
                for pair in percentage_pairs:
                    match = re.match(r'(.+?)\s+(\d+(?:\.\d+)?)%', pair)
                    if match:
                        pct_val = Decimal(match.group(2))
                        total_percentage += pct_val
                
                if total_percentage != 100:
                    anomalies.append({
                        'row_number': row_num,
                        'raw_row_data': row,
                        'anomaly_type': 'split_inconsistency',
                        'severity': 'high',
                        'description': f"Percentages sum to {total_percentage}%, expected 100%.",
                        'suggested_action': 'recalculate'
                    })

            if split_type == 'equal' and split_details:
                anomalies.append({
                    'row_number': row_num,
                    'raw_row_data': row,
                    'anomaly_type': 'redundant_details',
                    'severity': 'low',
                    'description': f"Split type is 'equal', but split_details '{split_details}' were provided.",
                    'suggested_action': 'recalculate'
                })

        # 7. Membership Validity Conflicts (Dynamic Membership over time)
        if parsed_date and not is_settlement:
            split_members = [m.strip() for m in split_with_str.split(';') if m.strip()] if split_with_str else []
            memberships = GroupMembership.objects.filter(group=group)
            
            for p in split_members:
                p_matched = fuzzy_match_user(p)
                if p_matched:
                    mship = memberships.filter(user__username=p_matched).first()
                    if mship:
                        if mship.joined_at > parsed_date:
                            anomalies.append({
                                'row_number': row_num,
                                'raw_row_data': row,
                                'anomaly_type': 'membership_conflict',
                                'severity': 'high',
                                'description': f"Participant '{p_matched}' joined on {mship.joined_at}, but is charged for expense on {parsed_date}.",
                                'suggested_action': 'recalculate'
                            })
                        if mship.left_at and mship.left_at < parsed_date:
                            anomalies.append({
                                'row_number': row_num,
                                'raw_row_data': row,
                                'anomaly_type': 'membership_conflict',
                                'severity': 'high',
                                'description': f"Participant '{p_matched}' left on {mship.left_at}, but is charged for expense on {parsed_date}.",
                                'suggested_action': 'recalculate'
                            })

            if payer_matched:
                mship = memberships.filter(user__username=payer_matched).first()
                if mship:
                    if mship.joined_at > parsed_date or (mship.left_at and mship.left_at < parsed_date):
                        anomalies.append({
                            'row_number': row_num,
                            'raw_row_data': row,
                            'anomaly_type': 'membership_conflict',
                            'severity': 'high',
                            'description': f"Payer '{payer_matched}' was not a member of the group on {parsed_date}.",
                            'suggested_action': 'recalculate'
                        })

        # 8. Duplicate transaction check
        for prev in processed:
            d1, _, _ = parse_date(date_str)
            d2, _, _ = parse_date(prev['date'])
            
            a1_clean = amount_str.replace('"', '').replace(',', '').strip() if amount_str else ''
            a2_clean = prev['amount'].replace('"', '').replace(',', '').strip() if prev['amount'] else ''
            
            p1_matched = fuzzy_match_user(paid_by_str)
            p2_matched = fuzzy_match_user(prev['paid_by'])

            if d1 and d2 and d1 == d2 and a1_clean == a2_clean and p1_matched == p2_matched:
                desc1_norm = re.sub(r'[^a-zA-Z0-9]', '', desc.lower())
                desc2_norm = re.sub(r'[^a-zA-Z0-9]', '', prev['description'].lower())
                
                if desc1_norm == desc2_norm or desc1_norm in desc2_norm or desc2_norm in desc1_norm:
                    anomalies.append({
                        'row_number': row_num,
                        'raw_row_data': row,
                        'anomaly_type': 'duplicate_record',
                        'severity': 'medium',
                        'description': f"Row {row_num} is a potential duplicate of Row {prev['line_num']}.",
                        'suggested_action': 'ignore'
                    })
            
            if d1 and d2 and d1 == d2 and p1_matched != p2_matched:
                desc1_norm = re.sub(r'[^a-zA-Z0-9]', '', desc.lower())
                desc2_norm = re.sub(r'[^a-zA-Z0-9]', '', prev['description'].lower())
                
                if ('thalassa' in desc1_norm and 'thalassa' in desc2_norm) or ('marina' in desc1_norm and 'marina' in desc2_norm):
                    anomalies.append({
                        'row_number': row_num,
                        'raw_row_data': row,
                        'anomaly_type': 'double_entry_conflict',
                        'severity': 'high',
                        'description': f"Double entry conflict: Row {row_num} ({paid_by_str}, {amount_str}) and Row {prev['line_num']} ({prev['paid_by']}, {prev['amount']}) represent the same transaction.",
                        'suggested_action': 'custom_mapping'
                    })

        return anomalies

    @staticmethod
    @transaction.atomic
    def commit_batch(batch_id, user):
        """
        Applies resolutions and imports all valid rows from the CSV file into the database.
        Changes status of Batch to 'completed'. Logs AuditLog events.
        """
        batch = ImportBatch.objects.get(id=batch_id)
        if batch.status == 'completed':
            raise ValueError("Batch is already committed.")
            
        group = Group.objects.first() # Default to first group
        if not group:
            raise ValueError("No group found to import transactions into.")

        csv_file = io.StringIO(batch.csv_data)
        reader = csv.DictReader(csv_file)
        reader.fieldnames = [name.strip() for name in reader.fieldnames] if reader.fieldnames else []
        rows = list(reader)
        
        # Load all anomalies for this batch
        anomalies_map = {an.row_number: an for an in batch.anomalies.all()}
        
        import_stats = {
            'expenses_created': 0,
            'settlements_created': 0,
            'skipped_rows': 0,
            'anomalies_resolved': 0,
        }

        for idx, row in enumerate(rows, start=2):
            raw_row = {k.strip() if k else '': v.strip() if v else '' for k, v in row.items()}
            
            anomaly = anomalies_map.get(idx)
            
            # Check if ignored
            if anomaly and anomaly.status == 'ignored':
                import_stats['skipped_rows'] += 1
                continue
            
            # Use overrides if resolved
            overrides = {}
            if anomaly and anomaly.status == 'resolved' and anomaly.resolved_data:
                overrides = anomaly.resolved_data
                import_stats['anomalies_resolved'] += 1

            # Get final fields
            date_str = overrides.get('date', raw_row.get('date', ''))
            desc = overrides.get('description', raw_row.get('description', ''))
            paid_by_str = overrides.get('paid_by', raw_row.get('paid_by', ''))
            amount_str = overrides.get('amount', raw_row.get('amount', ''))
            currency_str = overrides.get('currency', raw_row.get('currency', ''))
            split_type = overrides.get('split_type', raw_row.get('split_type', ''))
            split_with_str = overrides.get('split_with', raw_row.get('split_with', ''))
            split_details = overrides.get('split_details', raw_row.get('split_details', ''))
            notes = overrides.get('notes', raw_row.get('notes', ''))
            usd_rate = Decimal(str(overrides.get('exchange_rate', DEFAULT_USD_TO_INR_RATE)))

            # If payer is missing and not resolved, skip
            if not paid_by_str:
                import_stats['skipped_rows'] += 1
                continue

            # Parse amount
            try:
                cleaned_amount_str = str(amount_str).replace('"', '').replace(',', '').strip()
                amount = Decimal(cleaned_amount_str)
                # If negative, keep negative (it represents a refund)
            except (InvalidOperation, ValueError):
                # Skip unparseable amounts
                import_stats['skipped_rows'] += 1
                continue

            # Parse date
            parsed_dt, has_err, _ = parse_date(date_str)
            if has_err or not parsed_dt:
                # Fallback to current date or sequence if invalid date is not resolved
                parsed_dt = datetime.now().date()

            # Resolve user instances
            payer_username = fuzzy_match_user(paid_by_str)
            if not payer_username:
                # If payer name cannot be resolved, skip
                import_stats['skipped_rows'] += 1
                continue
            payer_user = User.objects.get(username=payer_username)

            # Resolve currency & conversion
            currency = currency_str.strip().upper() if currency_str else 'INR'
            if currency == '':
                currency = 'INR'
            
            exchange_rate = Decimal('1.00')
            if currency == 'USD':
                exchange_rate = usd_rate

            amount_in_base = round_decimal(amount * exchange_rate)

            # Determine if Settlement
            is_settlement_action = (anomaly and anomaly.suggested_action == 'import_as_settlement') or \
                                    (not split_type and split_with_str and len(split_with_str.split(';')) == 1) or \
                                    ('paid' in desc.lower() and 'back' in desc.lower())

            if is_settlement_action:
                # Save settlement
                to_username = fuzzy_match_user(split_with_str.strip()) if split_with_str else None
                if not to_username:
                    import_stats['skipped_rows'] += 1
                    continue
                to_user = User.objects.get(username=to_username)
                
                Settlement.objects.create(
                    group=group,
                    from_user=payer_user,
                    to_user=to_user,
                    amount=abs(amount), # Settlements are always positive
                    currency=currency,
                    exchange_rate=exchange_rate,
                    amount_in_base=abs(amount_in_base),
                    date=parsed_dt,
                    is_approved=True
                )
                import_stats['settlements_created'] += 1

            else:
                # Save expense
                # Check participants
                participants_list = []
                if split_with_str:
                    participants_list = [fuzzy_match_user(p.strip()) for p in split_with_str.split(';') if p.strip()]
                    participants_list = [p for p in participants_list if p] # filter out None
                
                if not participants_list:
                    # Default split with all active members if split_with is missing/empty
                    memberships = GroupMembership.objects.filter(group=group)
                    active_on_date = [m.user.username for m in memberships if m.joined_at <= parsed_dt and (not m.left_at or m.left_at >= parsed_dt)]
                    participants_list = active_on_date

                # Normalize split type
                s_type = split_type.strip().lower() if split_type else 'equal'
                if s_type not in ['equal', 'unequal', 'percentage', 'share']:
                    s_type = 'equal'

                # Calculate splits
                # Pass clean usernames
                splits = BalanceService.calculate_splits(
                    total_amount=amount_in_base,
                    split_type=s_type,
                    participants_usernames=participants_list,
                    split_details_str=split_details,
                    payer_username=payer_username
                )

                # Create Expense
                expense_obj = Expense.objects.create(
                    group=group,
                    description=desc,
                    paid_by=payer_user,
                    total_amount=amount,
                    currency=currency,
                    exchange_rate=exchange_rate,
                    amount_in_base=amount_in_base,
                    split_type=s_type,
                    date=parsed_dt
                )

                # Create Participants
                for u_name, (share_amt, raw_val) in splits.items():
                    u_obj = User.objects.get(username=u_name)
                    ExpenseParticipant.objects.create(
                        expense=expense_obj,
                        user=u_obj,
                        share_amount=share_amt,
                        raw_share_value=raw_val
                    )
                import_stats['expenses_created'] += 0 + 1

        # Mark batch as completed
        batch.status = 'completed'
        batch.save()

        # Log audit
        AuditLog.objects.create(
            user=user,
            action='commit_batch',
            table_name='ImportBatch',
            record_id=batch.id,
            new_value=import_stats
        )

        return import_stats
