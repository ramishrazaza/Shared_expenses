from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from django.contrib.auth import get_user_model
from expenses.models import Group, GroupMembership, Expense, ExpenseParticipant, Settlement

User = get_user_model()

def round_decimal(val):
    if val is None:
        return Decimal('0.00')
    return Decimal(val).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class BalanceService:
    @staticmethod
    def calculate_splits(total_amount, split_type, participants_usernames, split_details_str=None, payer_username=None):
        """
        Calculates individual shares (Decimal) for an expense.
        Handles remainder adjustments to prevent rounding discrepancies.
        
        Returns a dict: {username: (share_amount, raw_share_value)}
        """
        total_amount = Decimal(str(total_amount))
        count = len(participants_usernames)
        if count == 0:
            return {}

        shares = {}
        
        if split_type == 'equal':
            # Equal split
            base_share = round_decimal(total_amount / Decimal(str(count)))
            # Initialize all shares
            for u in participants_usernames:
                shares[u] = (base_share, Decimal('1.00'))
            
            # Remainder adjustment
            allocated_sum = sum(shares[u][0] for u in participants_usernames)
            diff = total_amount - allocated_sum
            if diff != 0:
                # Add remainder to the payer if specified, else the first participant
                adj_user = payer_username if (payer_username and payer_username in shares) else participants_usernames[0]
                current_share, raw_val = shares[adj_user]
                shares[adj_user] = (round_decimal(current_share + diff), raw_val)

        elif split_type == 'percentage':
            # Percentage split (e.g., split_details_str: "Aisha 30; Rohan 30; Priya 30; Meera 10")
            pct_map = {}
            if split_details_str:
                # Parse pairs like "Aisha 30%" or "Aisha 30"
                pairs = [p.strip() for p in split_details_str.split(';') if p.strip()]
                for pair in pairs:
                    parts = pair.replace('%', '').split()
                    if len(parts) >= 2:
                        u_name = " ".join(parts[:-1]).strip()
                        val = Decimal(parts[-1].strip())
                        pct_map[u_name] = val

            # Fill missing with 0
            for u in participants_usernames:
                if u not in pct_map:
                    pct_map[u] = Decimal('0.00')

            # Normalize percentages if they sum to other than 100
            total_pct = sum(pct_map.values())
            if total_pct == 0:
                total_pct = Decimal('100.00') # prevent division by zero

            # Calculate shares
            for u in participants_usernames:
                pct = pct_map[u]
                share_val = round_decimal(total_amount * pct / total_pct)
                shares[u] = (share_val, pct)

            # Remainder adjustment
            allocated_sum = sum(shares[u][0] for u in participants_usernames)
            diff = total_amount - allocated_sum
            if diff != 0:
                adj_user = payer_username if (payer_username and payer_username in shares) else participants_usernames[0]
                current_share, raw_val = shares[adj_user]
                shares[adj_user] = (round_decimal(current_share + diff), raw_val)

        elif split_type == 'share':
            # Split by shares/ratios (e.g., split_details_str: "Aisha 1; Rohan 2; Priya 1; Dev 2")
            share_map = {}
            if split_details_str:
                pairs = [p.strip() for p in split_details_str.split(';') if p.strip()]
                for pair in pairs:
                    parts = pair.split()
                    if len(parts) >= 2:
                        u_name = " ".join(parts[:-1]).strip()
                        val = Decimal(parts[-1].strip())
                        share_map[u_name] = val
            
            # Fill missing with default 1 share
            for u in participants_usernames:
                if u not in share_map:
                    share_map[u] = Decimal('1.00')

            total_shares = sum(share_map.values())
            if total_shares == 0:
                total_shares = Decimal('1.00')

            for u in participants_usernames:
                sh = share_map[u]
                share_val = round_decimal(total_amount * sh / total_shares)
                shares[u] = (share_val, sh)

            # Remainder adjustment
            allocated_sum = sum(shares[u][0] for u in participants_usernames)
            diff = total_amount - allocated_sum
            if diff != 0:
                adj_user = payer_username if (payer_username and payer_username in shares) else participants_usernames[0]
                current_share, raw_val = shares[adj_user]
                shares[adj_user] = (round_decimal(current_share + diff), raw_val)

        elif split_type == 'unequal':
            # Unequal/Direct split (e.g., split_details_str: "Rohan 700; Priya 400; Meera 400")
            amt_map = {}
            if split_details_str:
                pairs = [p.strip() for p in split_details_str.split(';') if p.strip()]
                for pair in pairs:
                    parts = pair.split()
                    if len(parts) >= 2:
                        u_name = " ".join(parts[:-1]).strip()
                        val = Decimal(parts[-1].strip())
                        amt_map[u_name] = val
            
            # Fill missing with 0
            for u in participants_usernames:
                if u not in amt_map:
                    amt_map[u] = Decimal('0.00')

            for u in participants_usernames:
                share_val = round_decimal(amt_map[u])
                shares[u] = (share_val, share_val)

            # Note: For unequal splits, we do NOT automatically adjust remainders,
            # but we assume the values sum to total_amount. If they don't, we can log it.
            allocated_sum = sum(shares[u][0] for u in participants_usernames)
            diff = total_amount - allocated_sum
            if diff != 0:
                # Force adjust on the payer or first member
                adj_user = payer_username if (payer_username and payer_username in shares) else participants_usernames[0]
                current_share, raw_val = shares[adj_user]
                shares[adj_user] = (round_decimal(current_share + diff), raw_val)

        return shares

    @staticmethod
    def get_group_net_balances(group_id):
        """
        Calculates the net balance for each user in the group.
        Net Balance = Paid Expenses + Received Settlements - Owed Expenses - Paid Settlements
        """
        group = Group.objects.get(id=group_id)
        users = User.objects.filter(memberships__group=group).distinct()
        
        balances = {}
        for u in users:
            balances[u.username] = Decimal('0.00')

        # 1. Add credit for expenses paid by the user
        expenses_paid = Expense.objects.filter(group=group, is_deleted=False).values('paid_by__username').annotate(total=Sum('amount_in_base'))
        for ep in expenses_paid:
            username = ep['paid_by__username']
            if username in balances:
                balances[username] += round_decimal(ep['total'])

        # 2. Subtract debit for expenses the user is a participant of
        expenses_owed = ExpenseParticipant.objects.filter(expense__group=group, expense__is_deleted=False).values('user__username').annotate(total=Sum('share_amount'))
        for eo in expenses_owed:
            username = eo['user__username']
            if username in balances:
                balances[username] -= round_decimal(eo['total'])

        # 3. Add credit for received settlements (from_user -> to_user, so to_user gets credit)
        settlements_received = Settlement.objects.filter(group=group, is_approved=True).values('to_user__username').annotate(total=Sum('amount_in_base'))
        for sr in settlements_received:
            username = sr['to_user__username']
            if username in balances:
                balances[username] += round_decimal(sr['total'])

        # 4. Subtract debit for paid settlements (from_user -> to_user, so from_user gets debit / reduces debt)
        settlements_paid = Settlement.objects.filter(group=group, is_approved=True).values('from_user__username').annotate(total=Sum('amount_in_base'))
        for sp in settlements_paid:
            username = sp['from_user__username']
            if username in balances:
                balances[username] -= round_decimal(sp['total'])

        # Round all balances to 2 decimals
        return {k: round_decimal(v) for k, v in balances.items()}

    @staticmethod
    def get_simplified_debts(group_id):
        """
        Aisha's requirement: "Who pays whom, how much, done."
        Simplifies debts in the group using standard flow minimization.
        """
        net_balances = BalanceService.get_group_net_balances(group_id)
        
        # Split into debtors and creditors
        debtors = []
        creditors = []
        for name, bal in net_balances.items():
            if bal < -0.01:
                # Debtors have negative balance (need to pay)
                debtors.append({'name': name, 'balance': -bal}) # store as positive for calculation
            elif bal > 0.01:
                # Creditors have positive balance (need to be paid)
                creditors.append({'name': name, 'balance': bal})

        # Greedy flow simplification
        simplified_settlements = []
        
        # Sort to simplify largest first
        debtors.sort(key=lambda x: x['balance'], reverse=True)
        creditors.sort(key=lambda x: x['balance'], reverse=True)

        d_idx, c_idx = 0, 0
        while d_idx < len(debtors) and c_idx < len(creditors):
            debtor = debtors[d_idx]
            creditor = creditors[c_idx]
            
            amount_to_pay = min(debtor['balance'], creditor['balance'])
            
            if amount_to_pay > 0.01:
                simplified_settlements.append({
                    'from_user': debtor['name'],
                    'to_user': creditor['name'],
                    'amount': round_decimal(amount_to_pay),
                    'currency': 'INR'
                })
            
            # Deduct from balances
            debtor['balance'] -= amount_to_pay
            creditor['balance'] -= amount_to_pay
            
            # Advance indices
            if debtor['balance'] < 0.01:
                d_idx += 1
            if creditor['balance'] < 0.01:
                c_idx += 1

        return simplified_settlements

    @staticmethod
    def get_user_balance_trace(group_id, username):
        """
        Rohan's requirement: "No magic numbers. If the app says I owe Rs. 2300,
        I want to see exactly which expenses make that up."
        
        Returns a detailed ledger explaining every credit and debit contributing
        to the user's final net balance.
        """
        group = Group.objects.get(id=group_id)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return {'error': 'User not found'}

        ledger = []
        
        # 1. Fetch all expenses paid by this user (Credits)
        paid_expenses = Expense.objects.filter(group=group, paid_by=user, is_deleted=False).order_by('date')
        for exp in paid_expenses:
            # We calculate their net contribution = total_amount - user's own share
            # User pays total_amount but owes their own share, so net credit = total_amount - own_share
            own_share_rec = ExpenseParticipant.objects.filter(expense=exp, user=user).first()
            own_share = own_share_rec.share_amount if own_share_rec else Decimal('0.00')
            net_credit = exp.amount_in_base - own_share

            ledger.append({
                'date': exp.date,
                'type': 'expense_paid',
                'description': exp.description,
                'total_amount': exp.total_amount,
                'currency': exp.currency,
                'amount_in_base': exp.amount_in_base,
                'user_share': own_share,
                'impact': round_decimal(net_credit), # positive credit
                'details': f"Paid {exp.total_amount} {exp.currency} (Your share: {own_share} INR)"
            })

        # 2. Fetch all expenses shared by this user paid by OTHERS (Debts)
        shared_expenses = ExpenseParticipant.objects.filter(
            expense__group=group,
            user=user,
            expense__is_deleted=False
        ).exclude(expense__paid_by=user).order_by('expense__date')

        for ep in shared_expenses:
            exp = ep.expense
            ledger.append({
                'date': exp.date,
                'type': 'expense_owed',
                'description': exp.description,
                'total_amount': exp.total_amount,
                'currency': exp.currency,
                'amount_in_base': exp.amount_in_base,
                'user_share': ep.share_amount,
                'impact': -round_decimal(ep.share_amount), # negative debit
                'details': f"Paid by {exp.paid_by.username} (Your share: {ep.share_amount} INR)"
            })

        # 3. Fetch all settlements paid by this user (Reduces Debt / Credit debit)
        paid_settlements = Settlement.objects.filter(group=group, from_user=user, is_approved=True).order_by('date')
        for setl in paid_settlements:
            ledger.append({
                'date': setl.date,
                'type': 'settlement_paid',
                'description': f"Settlement to {setl.to_user.username}",
                'total_amount': setl.amount,
                'currency': setl.currency,
                'amount_in_base': setl.amount_in_base,
                'user_share': Decimal('0.00'),
                'impact': -round_decimal(setl.amount_in_base), # reduces overall cash, represents cash outflow
                'details': f"You settled {setl.amount} {setl.currency} to {setl.to_user.username}"
            })

        # 4. Fetch all settlements received by this user (Credit / cash inflow)
        rec_settlements = Settlement.objects.filter(group=group, to_user=user, is_approved=True).order_by('date')
        for setl in rec_settlements:
            ledger.append({
                'date': setl.date,
                'type': 'settlement_received',
                'description': f"Settlement from {setl.from_user.username}",
                'total_amount': setl.amount,
                'currency': setl.currency,
                'amount_in_base': setl.amount_in_base,
                'user_share': Decimal('0.00'),
                'impact': round_decimal(setl.amount_in_base), # positive cash inflow/reduction of credit
                'details': f"Received {setl.amount} {setl.currency} from {setl.from_user.username}"
            })

        # Sort ledger by date
        ledger.sort(key=lambda x: x['date'])
        
        # Calculate running balance
        # A positive net balance means they are owed money.
        # A negative net balance means they owe money.
        running_bal = Decimal('0.00')
        for item in ledger:
            # Let's adjust impact meaning:
            # If user paid an expense, they are owed (impact is positive credit).
            # If user owes a share on someone else's expense, they owe money (impact is negative debit).
            # If user paid a settlement (settlement_paid), they transferred cash to someone else, which REDUCES what they owe (impact should be positive to reduce debt, or let's model it as: Net Balance = Paid Expenses - Owed Expenses + Received Settlements - Paid Settlements... wait!
            # Wait, let's think:
            # If Rohan owes 2300, his balance is -2300.
            # If he pays a settlement of 2300 to Aisha, his new balance is 0.
            # So, paying a settlement (+2300) increases his balance towards 0.
            # Thus, impact of settlement_paid is POSITIVE (+2300) on his balance!
            # Conversely, receiving a settlement (settlement_received) means someone paid Rohan, which reduces what Rohan is owed (reduces his positive credit). So receiving a settlement has a NEGATIVE impact (-2300) on his balance!
            # Let's verify this formula:
            # Net Balance = + (Paid Expense - Own Share) [Credit]
            #               - (Shared Expense Share paid by others) [Debit]
            #               + (Settlement Paid) [Reduces Debt/Increases Balance]
            #               - (Settlement Received) [Reduces Credit/Decreases Balance]
            # Let's double check.
            # Suppose Rohan owes Aisha 2300.
            # Rohan's ledger:
            # - Shared Expense (paid by Aisha): share is 2300. impact = -2300. Running balance = -2300.
            # - Settlement paid to Aisha: 2300. impact = +2300. Running balance = 0.
            # Yes! This matches!
            # Let's adjust impact values in ledger items:
            pass

        # Let's rewrite ledger calculations with correct signs:
        final_ledger = []
        running_bal = Decimal('0.00')
        
        for item in ledger:
            impact = Decimal('0.00')
            if item['type'] == 'expense_paid':
                # Paid by user. Impact = Total Amount in Base - Own Share
                impact = item['amount_in_base'] - item['user_share']
            elif item['type'] == 'expense_owed':
                # Paid by others, user owes share. Impact = - Share Amount
                impact = -item['user_share']
            elif item['type'] == 'settlement_paid':
                # User pays cash to settle debt. This increases their balance (makes it less negative). Impact = + Amount
                impact = item['amount_in_base']
            elif item['type'] == 'settlement_received':
                # User receives cash. This reduces their credit. Impact = - Amount
                impact = -item['amount_in_base']
                
            running_bal += round_decimal(impact)
            
            final_ledger.append({
                'date': item['date'].strftime('%Y-%m-%d'),
                'type': item['type'],
                'description': item['description'],
                'total_amount': float(item['total_amount']),
                'currency': item['currency'],
                'amount_in_base': float(item['amount_in_base']),
                'impact': float(round_decimal(impact)),
                'running_balance': float(round_decimal(running_bal)),
                'details': item['details']
            })

        return {
            'username': username,
            'net_balance': float(round_decimal(running_bal)),
            'ledger': final_ledger
        }
