'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random


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
        pass

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
        pass

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
            
            # If opponent has raised (continue_cost > 0), decide whether to call or fold
            if continue_cost > 0:
                if hand_strength == 'set_flush_straight':
                    # Always call with set/flush/straight
                    return CallAction()
                elif hand_strength == 'top_pair':
                    # Always call with top pair
                    return CallAction()
                elif hand_strength == 'mid_pair':
                    # Always call with mid pair
                    return CallAction()
                elif hand_strength == 'any_pair':
                    # Always call with any pair
                    return CallAction()
                elif hand_strength == 'nothing':
                    # Call if continue_cost < 10, or fold on 2nd to last street if continue_cost > 0
                    # Streets: 0=preflop, 4=post-discard, 5=turn, 6=river
                    # 2nd to last street would be turn (5) if we're on river (6)
                    is_second_to_last = (street == 5)  # Turn is 2nd to last before river
                    if continue_cost < 10:
                        return CallAction()
                    elif is_second_to_last and continue_cost > 0:
                        return FoldAction()
                    else:
                        return CallAction()
                else:
                    return CallAction()
            
            # If we can bet/raise (continue_cost == 0)
            if hand_strength == 'set_flush_straight':
                # Raise by 50, or all-in if pot > 200
                if pot_size > 200:
                    return RaiseAction(max_raise)  # All in
                else:
                    raise_amount = min(my_pip + 50, max_raise)
                    raise_amount = max(raise_amount, min_raise)  # Ensure at least min_raise
                    return RaiseAction(raise_amount)
            elif hand_strength == 'top_pair':
                # Bet 30, or all-in if pot > 200
                if pot_size > 200:
                    return RaiseAction(max_raise)  # All in
                else:
                    raise_amount = min(my_pip + 30, max_raise)
                    raise_amount = max(raise_amount, min_raise)  # Ensure at least min_raise
                    return RaiseAction(raise_amount)
            elif hand_strength == 'mid_pair':
                # Bet 10
                raise_amount = min(my_pip + 10, max_raise)
                raise_amount = max(raise_amount, min_raise)  # Ensure at least min_raise
                return RaiseAction(raise_amount)
            elif hand_strength == 'any_pair':
                # Just call (check if possible, otherwise call)
                if CheckAction in legal_actions:
                    return CheckAction()
                return CallAction()
            elif hand_strength == 'nothing':
                # Call if continue_cost < 10 (but continue_cost is 0 here, so check)
                if CheckAction in legal_actions:
                    return CheckAction()
                return CallAction()
            else:
                if CheckAction in legal_actions:
                    return CheckAction()
                return CallAction()
        
        if CheckAction in legal_actions:  # check-call
            return CheckAction()
        
        # If we need to call and have nothing, check conditions
        if continue_cost > 0:
            hand_strength = self.evaluate_hand_strength(my_cards, board_cards)
            if hand_strength == 'nothing':
                # Call if continue_cost < 10, or fold on 2nd to last street if continue_cost > 0
                is_second_to_last = (street == 5)  # Turn is 2nd to last before river
                if continue_cost < 10:
                    return CallAction()
                elif is_second_to_last and continue_cost > 0:
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
        Returns: 'set_flush_straight', 'top_pair', 'mid_pair', 'any_pair', 'nothing'
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
        
        # Check for flush (5 cards of same suit)
        suit_counts = {}
        for suit in all_suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        has_flush = any(count >= 5 for count in suit_counts.values())
        
        # Check for straight
        rank_values = sorted(set([rank_to_value[rank] for rank in all_ranks]))
        has_straight = False
        if len(rank_values) >= 5:
            # Check for 5 consecutive ranks
            for i in range(len(rank_values) - 4):
                if rank_values[i+4] - rank_values[i] == 4:
                    has_straight = True
                    break
            # Check for A-2-3-4-5 straight (wheel)
            if not has_straight:
                wheel_ranks = [rank_to_value['A'], rank_to_value['2'], rank_to_value['3'], 
                              rank_to_value['4'], rank_to_value['5']]
                if all(rv in rank_values for rv in wheel_ranks):
                    has_straight = True
        
        # Check for sets (3 of a kind) and pairs
        rank_counts = {}
        for rank in all_ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        # Find sets (3 of a kind)
        sets = [rank for rank, count in rank_counts.items() if count >= 3]
        has_set = len(sets) > 0
        
        # Determine hand strength - check best hands first
        if has_set or has_flush or has_straight:
            return 'set_flush_straight'
        
        # Find pairs
        pairs = [rank for rank, count in rank_counts.items() if count == 2]
        if not pairs:
            return 'nothing'
        
        pairs.sort(key=lambda r: rank_to_value[r], reverse=True)  # Sort by rank, highest first
        
        # Check which pairs we have (need to see if our cards make the pair)
        board_ranks = [card[0] for card in board_cards]
        my_ranks = [card[0] for card in my_cards]
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
        if pairs:
            # Check if any of our cards are in the pairs
            for pair_rank in pairs:
                if pair_rank in my_ranks:
                    return 'any_pair'
        
        return 'nothing'


if __name__ == '__main__':
    run_bot(Player(), parse_args())