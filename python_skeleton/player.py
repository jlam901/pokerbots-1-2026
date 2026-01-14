'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random

def get_low(cards):
    """
    Given a list of cards, returns the lowest one.
    """
    id = 0
    for i, card in enumerate(cards):
        if card[0] < cards[id][0]:
            id = i
    return i


def standardize(cards):
    dic = {
        str(i): i for i in range(2, 10)
    }
    dic["T"] = 10
    dic["J"] = 11
    dic["Q"] = 12
    dic["K"] = 13
    dic["A"] = 14

    

def handle_same_cards(mycards, comcards):
    paired_indices = set()
    mycards_ordered = sorted((value, idx) for idx, value in enumerate(mycards))

    for card, i in mycards_ordered:
        for com in comcards:
            if card[0] == com[0]:
                paired_indices.append(i)
    
    for card, i in mycards_ordered:
        if i not in paired_indices:
            return (len(paired_indices) > 0), i
    return True, 0
            

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
        
        ranks="234567889TJQKA"
        # Only use DiscardAction if it's in legal_actions (which already checks street)
        # legal_actions() returns DiscardAction only when street is 2 or 3
        if DiscardAction in legal_actions:
            if board_cards[0][1] == board_cards[1][1]:
                suit_dict = {}
                playable_cards = my_cards + board_cards
                for i in playable_cards:
                    if i[1] in suit_dict:
                        count = suit_dict[i] + 1
                    else:
                        suit_dict[i] = 1
                for i in suit_dict:
                    if suit_dict[i] == 4:
                        for 

            # keep pair and discard from remaining
            pair_exists, id = handle_same_cards(my_cards, board_cards)
            return DiscardAction(id)

            #discard worst
            rank_list=[]
            num_cards=len(my_cards)
            for card in range(num_cards):
                rank_list.append(ranks.index(my_cards[card][0]))
            min_rank_idx=rank_list.index(min(rank_list))
            return DiscardAction(min_rank_idx)
        if street==0:
            if CheckAction in legal_actions:
                return CheckAction()
            else:
                return CallAction()
        if RaiseAction in legal_actions:
            # the smallest and largest numbers of chips for a legal bet/raise
            min_raise, max_raise = round_state.raise_bounds()
            min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
            max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
            l
tseegr
            for i in board_cards:
                
        if CheckAction in legal_actions:  # check-call
            return CheckAction()
        if random.random() < 0.25:
            return FoldAction()
        return CallAction()


if __name__ == '__main__':
    run_bot(Player(), parse_args())