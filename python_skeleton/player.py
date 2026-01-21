'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random
import math


class Player(Bot):
    '''
    A pokerbot.
    '''

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        # Table: street -> hand_strength -> {'sum': total_contribution, 'count': observations}
        self.opp_behavior_table = {}
        for st in [0, 2, 3, 4, 5, 6]:
            self.opp_behavior_table[st] = {
                'quads': {'sum': 0.0, 'count': 0},
                'fullhouse': {'sum': 0.0, 'count': 0},
                'flush': {'sum': 0.0, 'count': 0},
                'straight': {'sum': 0.0, 'count': 0},
                'set': {'sum': 0.0, 'count': 0},
                'top_pair': {'sum': 0.0, 'count': 0},
                'mid_pair': {'sum': 0.0, 'count': 0},
                'any_pair': {'sum': 0.0, 'count': 0},
                'nothing': {'sum': 0.0, 'count': 0},
            }

    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        # the total number of seconds your bot has left to play this game
        game_clock = game_state.game_clock
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        big_blind = bool(active)  # True if you are the big blind
        pass

    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0,2,3,4,5,6 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        # opponent's cards or [] if not revealed
        opp_cards = previous_state.hands[1-active]
        # Update opponent behavior table only if their hand is revealed
        if opp_cards:
            self._update_opponent_behavior(previous_state, opp_cards, 1 - active)

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        
        # PRIORITY CHECK: If cumulative delta exceeds threshold, fold at soonest possible moment
        cumulative_delta = game_state.bankroll  # Total chips gained/lost from previous rounds
        remaining_rounds = NUM_ROUNDS - game_state.round_num + 1  # +1 because round_num is 1-indexed
        threshold = math.ceil((remaining_rounds / 2) * 3)
        
        if cumulative_delta > threshold:
            # Fold at the soonest possible moment (highest priority)
            if FoldAction in legal_actions:
                return FoldAction()
            # If we can't fold yet (e.g., during discard phase), wait for next opportunity
            # But we'll still fold as soon as possible
        
        # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        street = round_state.street
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.board  # the board cards
        # the number of chips you have contributed to the pot this round of betting
        my_pip = round_state.pips[active]
        # the number of chips your opponent has contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]
        # the number of chips you have remaining
        my_stack = round_state.stacks[active]
        # the number of chips your opponent has remaining
        opp_stack = round_state.stacks[1-active]
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        # the number of chips you have contributed to the pot
        my_contribution = STARTING_STACK - my_stack
        # the number of chips your opponent has contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack

        # Only use DiscardAction if it's in legal_actions (which already checks street)
        # legal_actions() returns DiscardAction only when street is 2 or 3
        if DiscardAction in legal_actions:
            # Combine player's cards and board cards
            all_cards = my_cards + board_cards
            
            # Extract ranks and suits from all cards
            rank_order = "23456789TJQKA"
            all_ranks = [card[0] for card in all_cards]
            all_suits = [card[1] for card in all_cards]
            my_ranks = [card[0] for card in my_cards]
            my_suits = [card[1] for card in my_cards]
            
            # Count occurrences of each rank
            rank_counts = {}
            for rank in all_ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1
            
            # Check if player has 3 of the same card
            for rank in my_ranks:
                if rank_counts[rank] >= 3:
                    # Check if all 3 of my cards are the same rank
                    if my_ranks.count(rank) == 3:
                        return DiscardAction(0)
            
            # Check for flush draws (4 cards of the same suit)
            cards_in_flush_draw = set()
            suit_counts = {}
            for i, suit in enumerate(all_suits):
                suit_counts[suit] = suit_counts.get(suit, 0) + 1
            
            # Find suits with 4 cards (flush draw)
            flush_draw_suits = [suit for suit, count in suit_counts.items() if count == 4]
            if flush_draw_suits:
                flush_suit = flush_draw_suits[0]
                # Mark which of my cards are part of the flush draw
                for i, suit in enumerate(my_suits):
                    if suit == flush_suit:
                        cards_in_flush_draw.add(i)
            
            # Check for open-ended straight draws
            cards_in_straight_draw = set()
            # Convert ranks to numeric values for easier comparison
            rank_to_value = {rank: i for i, rank in enumerate(rank_order)}
            all_rank_values = sorted(set([rank_to_value[rank] for rank in all_ranks]))
            
            # Check for open-ended straight draws (4 consecutive ranks)
            for start_idx in range(len(all_rank_values) - 3):
                consecutive_ranks = all_rank_values[start_idx:start_idx + 4]
                # Check if they form 4 consecutive ranks (difference of 3 between first and last)
                if consecutive_ranks[-1] - consecutive_ranks[0] == 3:
                    first_rank_val = consecutive_ranks[0]
                    last_rank_val = consecutive_ranks[-1]
                    
                    # Check if it's open-ended (can be completed on either end)
                    # Can extend left if first_rank > 0 (not Ace)
                    can_extend_left = first_rank_val > 0
                    # Can extend right if last_rank < 12 (not King)
                    can_extend_right = last_rank_val < len(rank_order) - 1
                    
                    # Open-ended means we can complete on at least one end
                    if can_extend_left or can_extend_right:
                        # This is an open-ended straight draw
                        # Find which of my cards are part of this draw
                        draw_ranks = [rank_order[val] for val in consecutive_ranks]
                        for i, rank in enumerate(my_ranks):
                            if rank in draw_ranks:
                                cards_in_straight_draw.add(i)
            
            # If we have flush draw or straight draw, discard weakest card NOT in draws
            cards_in_draws = cards_in_flush_draw | cards_in_straight_draw
            if cards_in_draws:
                weakest_index = None
                weakest_rank_value = -1
                
                for i, rank in enumerate(my_ranks):
                    if i not in cards_in_draws:  # This card is not part of any draw
                        rank_value = rank_order.index(rank)
                        if weakest_index is None or rank_value < weakest_rank_value:
                            weakest_index = i
                            weakest_rank_value = rank_value
                
                # If all cards are in draws, discard the weakest one overall
                if weakest_index is None:
                    weakest_index = 0
                    weakest_rank_value = rank_order.index(my_ranks[0])
                    for i, rank in enumerate(my_ranks):
                        rank_value = rank_order.index(rank)
                        if rank_value < weakest_rank_value:
                            weakest_index = i
                            weakest_rank_value = rank_value
                
                return DiscardAction(weakest_index)
            
            # Fall back to pair logic if no draws
            # Find which of my cards are part of pairs (or better)
            cards_in_pairs = set()
            for i, rank in enumerate(my_ranks):
                if rank_counts[rank] >= 2:  # This card is part of a pair or better
                    cards_in_pairs.add(i)
            
            # Find the weakest card that is NOT in any pair
            weakest_index = None
            weakest_rank_value = -1
            
            for i, rank in enumerate(my_ranks):
                if i not in cards_in_pairs:  # This card is not part of any pair
                    rank_value = rank_order.index(rank)
                    if weakest_index is None or rank_value < weakest_rank_value:
                        weakest_index = i
                        weakest_rank_value = rank_value
            
            # If all cards are in pairs, discard the weakest one overall
            if weakest_index is None:
                weakest_index = 0
                weakest_rank_value = rank_order.index(my_ranks[0])
                for i, rank in enumerate(my_ranks):
                    rank_value = rank_order.index(rank)
                    if rank_value < weakest_rank_value:
                        weakest_index = i
                        weakest_rank_value = rank_value
            
            return DiscardAction(weakest_index)
        if RaiseAction in legal_actions:
            # the smallest and largest numbers of chips for a legal bet/raise
            min_raise, max_raise = round_state.raise_bounds()
            min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
            max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
            
            # Calculate pot size
            pot_size = my_contribution + opp_contribution
            
            # Evaluate hand strength
            hand_strength = self.evaluate_hand_strength(my_cards, board_cards)
            
            # After 100 rounds, estimate opponent's hand and adjust strategy
            adjusted_strength = hand_strength
            opp_estimated_strength = None
            if game_state.round_num > 100:
                opp_estimated_strength = self.opponent_hand_estimator(opp_pip, street, board_cards)
                comparison = self._compare_hand_strengths(hand_strength, opp_estimated_strength)
                
                if comparison < 0:  # Opponent is better
                    # Use betting logic for one strength below ours
                    adjusted_strength = self._get_strength_one_below(hand_strength)
                # If we're better or equal, use our actual strength
            
            # Determine target contribution for this round based on adjusted hand strength
            if adjusted_strength == 'quads':
                target_contribution = 60
            elif adjusted_strength == 'fullhouse':
                target_contribution = 60
            elif adjusted_strength == 'flush':
                target_contribution = 55
            elif adjusted_strength == 'straight':
                target_contribution = 50
            elif adjusted_strength == 'set':
                target_contribution = 45
            elif adjusted_strength == 'top_pair':
                target_contribution = 30
            elif adjusted_strength == 'mid_pair':
                target_contribution = 10
            else:  # any_pair or nothing
                target_contribution = 0
            
            # Special logic: if we have top pair or mid pair, and opponent could have 5 combo draw, and opponent is worse/equal, increase target to 70
            if game_state.round_num > 100 and opp_estimated_strength:
                if (hand_strength == 'top_pair' or hand_strength == 'mid_pair') and \
                   self._opponent_could_have_five_combo_draw(board_cards):
                    comparison = self._compare_hand_strengths(hand_strength, opp_estimated_strength)
                    if comparison >= 0:  # We're better or equal
                        target_contribution = 70
            
            # If opponent has raised (continue_cost > 0)
            if continue_cost > 0:
                # If we estimated opponent is better and we're worse, apply special logic
                if game_state.round_num > 100 and opp_estimated_strength and \
                   self._compare_hand_strengths(hand_strength, opp_estimated_strength) < 0:
                    # Never call above 10, fold if continue_cost > 10
                    if continue_cost > 10:
                        return FoldAction()
                    elif continue_cost <= 10:
                        return CallAction()
                
                # For weak hands, apply fold logic
                if adjusted_strength == 'any_pair' or adjusted_strength == 'nothing':
                    if continue_cost < 10:
                        return CallAction()
                    elif street == 4:
                        if continue_cost > 15:
                            return FoldAction()
                        else:
                            return CallAction()
                    elif (street == 5 or street == 6): # 2nd to last street would be turn (5) if we're on river (6)
                        return FoldAction()
                    else:
                        return CallAction()
                
                # For strong hands, we want our contribution to be >= target_contribution
                # Call would make our contribution = opp_pip
                # We want: max(opp_pip, target_contribution)
                call_contribution = opp_pip
                desired_contribution = max(call_contribution, target_contribution)
                
                if desired_contribution <= call_contribution:
                    # Just calling meets our target
                    return CallAction()
                else:
                    # We need to raise to meet our target
                    # Raise amount (absolute) should be desired_contribution
                    raise_amount = desired_contribution
                    # But we must respect minimum raise amount
                    raise_amount = max(raise_amount, min_raise)
                    # And we can't exceed maximum raise
                    raise_amount = min(raise_amount, max_raise)
                    return RaiseAction(raise_amount)
            
            # If we can bet/raise (continue_cost == 0)
            if target_contribution == 0:
                # Just check if possible, otherwise call
                if CheckAction in legal_actions:
                    return CheckAction()
                return CallAction()
            
            # We want to raise to target_contribution
            raise_amount = target_contribution
            # But we must respect minimum raise amount
            raise_amount = max(raise_amount, min_raise)
            # And we can't exceed maximum raise
            raise_amount = min(raise_amount, max_raise)
            return RaiseAction(raise_amount)
        
        if CheckAction in legal_actions:  # check-call
            return CheckAction()
        
        # If we need to call and have nothing, check conditions
        if continue_cost > 0:
            hand_strength = self.evaluate_hand_strength(my_cards, board_cards)
            
            # After 100 rounds, estimate opponent's hand and adjust strategy
            if game_state.round_num > 100:
                opp_estimated_strength = self.opponent_hand_estimator(opp_pip, street, board_cards)
                comparison = self._compare_hand_strengths(hand_strength, opp_estimated_strength)
                
                # If we're worse than opponent, never call above 10
                if comparison < 0:
                    if continue_cost > 10:
                        return FoldAction()
                    elif continue_cost <= 10:
                        return CallAction()
            
            if hand_strength == 'nothing' or hand_strength == 'any_pair':
                # Treat any_pair the same as nothing
                # Call if continue_cost < 10, or fold on 2nd to last street if continue_cost > 0
                if continue_cost < 10:
                    return CallAction()
                elif street == 4:
                    if continue_cost > 15:
                        return FoldAction()
                elif (street == 5 or street == 6): # 2nd to last street would be turn (5) if we're on river (6)
                    return FoldAction()
                else:
                    return CallAction()

            else:
                # Always call with any hand strength
                return CallAction()
        
        return CallAction()
    
    def evaluate_hand_strength(self, my_cards, board_cards):
        """
        Evaluate the best 5-card hand from my_cards + board_cards.
        Returns: 'quads', 'fullhouse', 'flush', 'straight', 'set', 'top_pair', 'mid_pair', 'any_pair', 'nothing'
        Power order: set < straight < flush < fullhouse < quads
        """
        if not board_cards:
            # Pre-flop: can only have pairs from hole cards
            my_ranks = [card[0] for card in my_cards]
            if len(set(my_ranks)) < len(my_ranks):
                return 'any_pair'
            return 'nothing'
        
        all_cards = my_cards + board_cards
        rank_order = "23456789TJQKA"
        rank_to_value = {rank: i for i, rank in enumerate(rank_order)}
        
        # Extract ranks and suits
        all_ranks = [card[0] for card in all_cards]
        all_suits = [card[1] for card in all_cards]
        my_ranks = [card[0] for card in my_cards]
        my_suits = [card[1] for card in my_cards]
        
        # Count ranks and suits
        rank_counts = {}
        for rank in all_ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        suit_counts = {}
        for suit in all_suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Check for quads (4 of a kind) - must have at least one of our cards
        for rank, count in rank_counts.items():
            if count >= 4:
                if any(my_rank == rank for my_rank in my_ranks):
                    return 'quads'
        
        # Check for full house (3 of a kind + pair) - must have at least one of our cards
        sets = [rank for rank, count in rank_counts.items() if count >= 3]
        pairs = [rank for rank, count in rank_counts.items() if count >= 2]
        has_fullhouse = False
        if sets and pairs:
            # Check if we contribute to the set or the pair
            for set_rank in sets:
                if any(my_rank == set_rank for my_rank in my_ranks):
                    has_fullhouse = True
                    break
            if not has_fullhouse:
                for pair_rank in pairs:
                    if pair_rank not in sets and any(my_rank == pair_rank for my_rank in my_ranks):
                        has_fullhouse = True
                        break
        if has_fullhouse:
            return 'fullhouse'
        
        # Check for flush (5 cards of same suit) - must have at least one of our cards
        flush_suit = None
        for suit, count in suit_counts.items():
            if count >= 5:
                if any(my_suit == suit for my_suit in my_suits):
                    flush_suit = suit
                    break
        if flush_suit:
            return 'flush'
        
        # Check for straight - must have at least one of our cards
        rank_values = sorted(set([rank_to_value[rank] for rank in all_ranks]))
        has_straight = False
        if len(rank_values) >= 5:
            # Check for 5 consecutive ranks
            for i in range(len(rank_values) - 4):
                straight_segment = rank_values[i:i+5]
                if straight_segment[-1] - straight_segment[0] == 4:
                    # Check if at least one of our cards contributes
                    if any(rank_to_value[my_rank] in straight_segment for my_rank in my_ranks):
                        has_straight = True
                        break
            # Check for A-2-3-4-5 straight (wheel)
            if not has_straight:
                wheel_ranks_values = [rank_to_value['A'], rank_to_value['2'], rank_to_value['3'], 
                              rank_to_value['4'], rank_to_value['5']]
                if all(rv in rank_values for rv in wheel_ranks_values):
                    if any(rank_to_value[my_rank] in wheel_ranks_values for my_rank in my_ranks):
                        has_straight = True
        if has_straight:
            return 'straight'
        
        # Check for set (3 of a kind) - must have at least one of our cards
        for set_rank in sets:
            if any(my_rank == set_rank for my_rank in my_ranks):
                return 'set'
        
        # Find pairs (excluding sets)
        pairs = [rank for rank, count in rank_counts.items() if count == 2]
        if not pairs:
            return 'nothing'
        
        pairs.sort(key=lambda r: rank_to_value[r], reverse=True)  # Sort by rank, highest first
        
        # Check which pairs we have (need to see if our cards make the pair)
        board_ranks = [card[0] for card in board_cards]
        board_rank_values = sorted([rank_to_value[r] for r in board_ranks], reverse=True) if board_ranks else []
        
        # Check if we have a pair with the highest board card (top pair)
        if board_rank_values:
            highest_board_rank_val = board_rank_values[0]
            highest_board_rank = rank_order[highest_board_rank_val]
            
            # Check if we have a pair with the highest board card
            if highest_board_rank in pairs and highest_board_rank in my_ranks:
                return 'top_pair'
            
            # Check for mid pair (2nd highest board card)
            if len(board_rank_values) >= 2:
                second_highest_board_rank_val = board_rank_values[1]
                second_highest_board_rank = rank_order[second_highest_board_rank_val]
                if second_highest_board_rank in pairs and second_highest_board_rank in my_ranks:
                    return 'mid_pair'
        
        # If we have any pair (but not top or mid pair)
        for pair_rank in pairs:
            if pair_rank in my_ranks:
                return 'any_pair'
        
        return 'nothing'

    # ---------------- Opponent behavior tracking ---------------- #

    def _compare_hand_strengths(self, strength1, strength2):
        """
        Compare two hand strengths. Returns:
        - 1 if strength1 > strength2
        - -1 if strength1 < strength2
        - 0 if strength1 == strength2
        Power order: set < straight < flush < fullhouse < quads
        """
        strength_order = {
            'quads': 8,
            'fullhouse': 7,
            'flush': 6,
            'straight': 5,
            'set': 4,
            'top_pair': 3,
            'mid_pair': 2,
            'any_pair': 1,
            'nothing': 0
        }
        val1 = strength_order.get(strength1, 0)
        val2 = strength_order.get(strength2, 0)
        if val1 > val2:
            return 1
        elif val1 < val2:
            return -1
        return 0

    def _get_strength_one_below(self, strength):
        """
        Get the hand strength one level below the given strength.
        """
        strength_hierarchy = ['quads', 'fullhouse', 'flush', 'straight', 'set', 'top_pair', 'mid_pair', 'any_pair', 'nothing']
        try:
            idx = strength_hierarchy.index(strength)
            if idx < len(strength_hierarchy) - 1:
                return strength_hierarchy[idx + 1]
        except ValueError:
            pass
        return strength  # Return same if can't go lower

    def _update_behavior_table(self, street, strength, contribution):
        """
        Update running mean table for opponent contributions per street and strength.
        """
        table_for_street = self.opp_behavior_table.get(street)
        if not table_for_street:
            return
        entry = table_for_street.get(strength)
        if entry is None:
            return
        entry['sum'] += contribution
        entry['count'] += 1

    def _update_opponent_behavior(self, final_round_state, opp_cards, opp_index):
        """
        Walk the round_state history, capture opponent contribution per street, and
        record the observed strength (using the same evaluator) at each street.
        Only called when opponent's hand is revealed.
        """
        # Traverse full history
        states = []
        cur = final_round_state
        while isinstance(cur, RoundState):
            states.append(cur)
            cur = cur.previous_state
        states.reverse()  # chronological

        # Keep the last state per street (final contribution on that street)
        street_state = {}
        for st in states:
            street_state[st.street] = st

        for street, state in street_state.items():
            opp_pip = state.pips[opp_index] if hasattr(state, 'pips') else 0
            board = state.board if hasattr(state, 'board') else []
            strength = self.evaluate_hand_strength(list(opp_cards), list(board))
            self._update_behavior_table(street, strength, opp_pip)

    def _get_possible_hands_from_board(self, board_cards):
        """
        Given the board, return all possible 5-card combo hands that could be made.
        Returns a list of possible hand strengths in order of likelihood.
        """
        if not board_cards:
            return ['nothing', 'any_pair', 'mid_pair', 'top_pair', 'set', 'straight', 'flush', 'fullhouse', 'quads']
        
        rank_order = "23456789TJQKA"
        rank_to_value = {rank: i for i, rank in enumerate(rank_order)}
        
        board_ranks = [card[0] for card in board_cards]
        board_suits = [card[1] for card in board_cards]
        
        possible_hands = []
        
        # Count ranks and suits on board
        rank_counts = {}
        for rank in board_ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        suit_counts = {}
        for suit in board_suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Check for possible quads (4 of same rank on board)
        if any(count >= 4 for count in rank_counts.values()):
            possible_hands.append('quads')
        
        # Check for possible full house (3 of one rank + 2 of another, or 3 of one rank on board)
        if any(count >= 3 for count in rank_counts.values()):
            if any(count >= 2 for rank, count in rank_counts.items() if count < 3):
                possible_hands.append('fullhouse')
            elif len(board_cards) >= 4:  # Could pair with hole card
                possible_hands.append('fullhouse')
        
        # Check for possible flush (4+ cards of same suit)
        if any(count >= 4 for count in suit_counts.values()):
            possible_hands.append('flush')
        
        # Check for possible straight (4 consecutive ranks)
        board_rank_values = sorted(set([rank_to_value[rank] for rank in board_ranks]))
        if len(board_rank_values) >= 4:
            for i in range(len(board_rank_values) - 3):
                if board_rank_values[i+3] - board_rank_values[i] <= 4:
                    possible_hands.append('straight')
                    break
        
        # Check for possible set (3 of same rank on board)
        if any(count >= 3 for count in rank_counts.values()):
            possible_hands.append('set')
        
        # Always possible to have pairs
        if any(count >= 2 for count in rank_counts.values()):
            possible_hands.append('top_pair')
            possible_hands.append('mid_pair')
            possible_hands.append('any_pair')
        
        possible_hands.append('nothing')
        
        # Return unique hands, ordered by strength
        strength_order = {
            'quads': 8, 'fullhouse': 7, 'flush': 6, 'straight': 5, 'set': 4,
            'top_pair': 3, 'mid_pair': 2, 'any_pair': 1, 'nothing': 0
        }
        unique_hands = []
        seen = set()
        for hand in sorted(possible_hands, key=lambda h: strength_order.get(h, 0), reverse=True):
            if hand not in seen:
                unique_hands.append(hand)
                seen.add(hand)
        
        return unique_hands if unique_hands else ['nothing']

    def opponent_hand_estimator(self, opp_contribution, street, board_cards):
        """
        Estimate opponent hand strength given their current contribution (pips), street, and board.
        Returns the most likely POSSIBLE hand based on board config and contribution pattern.
        """
        # Get possible hands from board
        possible_hands = self._get_possible_hands_from_board(board_cards)
        
        table_for_street = self.opp_behavior_table.get(street)
        if not table_for_street:
            # Return strongest possible hand if no data
            return possible_hands[0] if possible_hands else 'nothing'

        best_strength = 'nothing'
        best_diff = float('inf')
        
        # Only consider hands that are possible given the board
        for strength in possible_hands:
            data = table_for_street.get(strength)
            if not data or data['count'] == 0:
                continue
            mean_contribution = data['sum'] / data['count']
            diff = abs(opp_contribution - mean_contribution)
            if diff < best_diff:
                best_diff = diff
                best_strength = strength

        # If no match found, return strongest possible hand
        if best_strength == 'nothing' and possible_hands:
            return possible_hands[0]
        
        return best_strength

    def _opponent_could_have_five_combo_draw(self, board_cards):
        """
        Check if it's mathematically possible for the opponent to have a 5 combo draw
        (1 card away from quads, fullhouse, flush, straight, or set) based on the board alone.
        Returns True if the board configuration makes it possible for opponent to have such a draw.
        """
        if not board_cards or len(board_cards) < 2:
            return False
        
        rank_order = "23456789TJQKA"
        rank_to_value = {rank: i for i, rank in enumerate(rank_order)}
        
        board_ranks = [card[0] for card in board_cards]
        board_suits = [card[1] for card in board_cards]
        
        # Count ranks and suits on board
        rank_counts = {}
        for rank in board_ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        suit_counts = {}
        for suit in board_suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        # Check for quads draw possibility (3 of a kind on board - opponent could pair it)
        for rank, count in rank_counts.items():
            if count == 3:
                return True  # Opponent could have the 4th card
        
        # Check for full house draw possibility
        pairs = [rank for rank, count in rank_counts.items() if count == 2]
        sets = [rank for rank, count in rank_counts.items() if count >= 3]
        # If there's a pair and a set, or 2 pairs, opponent could complete full house
        if (sets and pairs) or len(pairs) >= 2:
            return True
        # If there's a set, opponent could pair any other rank
        if sets and len(board_cards) >= 3:
            return True
        
        # Check for flush draw possibility (4 cards of same suit on board)
        for suit, count in suit_counts.items():
            if count == 4:
                return True  # Opponent could have the 5th card of that suit
        
        # Check for straight draw possibility (4 consecutive ranks, or 4 ranks with 1 gap)
        board_rank_values = sorted(set([rank_to_value[rank] for rank in board_ranks]))
        if len(board_rank_values) >= 4:
            for i in range(len(board_rank_values) - 3):
                consecutive_ranks = board_rank_values[i:i+4]
                gap = consecutive_ranks[-1] - consecutive_ranks[0]
                # Open-ended (4 consecutive) or gutshot (gap of 4 with 1 missing in between)
                if gap == 3 or (gap == 4 and len(consecutive_ranks) == 4):
                    return True  # Opponent could complete the straight
        
        # Check for set draw possibility (pair on board - opponent could have the 3rd card)
        for rank, count in rank_counts.items():
            if count == 2:
                return True  # Opponent could have the 3rd card
        
        return False


if __name__ == '__main__':
    run_bot(Player(), parse_args())