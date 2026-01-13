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




#change below here
        #probablity of tossing a random card
        alpha=0.20
        #probability of raising
        beta=0.25
        #scale times opponent's bet (gamma>1)
        gamma=4
        #first action gamma
        theta=2
        #first action beta
        phi=0.30
        #probability of folding at any point
        delta=0.05
        rank = "23456789TJQKA"
        rank_list=[]
        starting_rank=-1
        for i in rank:
            starting_rank+=1
            rank_list.append(starting_rank)
        matching_cards=[]
        matching_cards_count={}
        for i in my_cards:
            matching_cards_count[rank_list[rank.index(i[0])]]=1
        for i in board_cards:
            matching_cards_count[rank_list[rank.index(i[0])]]=1
        for i in my_cards:
            if i[0] not in matching_cards:
                matching_cards.append(i[0])
            else:
                matching_cards_count[rank_list[rank.index(i[0])]]+=1
        for i in board_cards:
            if i[0] not in matching_cards:
                matching_cards.append(rank_list[rank.index(i[0])])
            else:
                matching_cards_count[int(i[0])]+=1
        for i in reversed(sorted(matching_cards_count.values())):
            if i==4:
                beta=1
                theta = 100
                gamma = 100
                delta = 0
                break
            if i==3:
                beta=0.9
                theta = 5
                gamma = 10
                delta = 0
                break
            if i==2:
                beta=0.5
                delta = 0
                break
        if street!=1:
            for i in board_cards:
                if rank.index(i[0])>=rank.index("Q"):
                    beta=0.7
                    break
        # Only use DiscardAction if it's in legal_actions (which already checks street)
        # legal_actions() returns DiscardAction only when street is 2 or 3
        if DiscardAction in legal_actions:
            if random.random()<(1-alpha):
                ranks = "23456789TJQKA" # order of ranks
                rank_list = [-1, -1, -1] # uninitialized

                for card in range(3): # loop through cards in hand
                    rank_list[card] = ranks.index(my_cards[card][0]) # get rank of each card

                # find the card with the minimum rank
                if rank_list[0] <= rank_list[1] and rank_list[0] <= rank_list[2]:
                    return DiscardAction(0)
                elif rank_list[1] <= rank_list[2]:
                    return DiscardAction(1)
                else:
                    return DiscardAction(2)
            #random discard
            else:
                random_discard=[0,1,2]
                return DiscardAction(random.choice(random_discard))
        #randomly folding
        if random.random() <= delta and street != 1:
            return FoldAction()
        if CheckAction in legal_actions:  # check-call
            if random.random()<=phi:
                #raise
                var = opp_pip
                if opp_pip==0:
                    var = opp_contribution + my_contribution
                    return RaiseAction(min(min_raise + (theta * var - min_raise) * random.random(), max_raise))
            else:
                #return check-call
                return CheckAction()
        if RaiseAction in legal_actions:
            # the smallest and largest numbers of chips for a legal bet/raise
            min_raise, max_raise = round_state.raise_bounds()
            min_cost = min_raise - my_pip  # the cost of a minimum bet/raise
            max_cost = max_raise - my_pip  # the cost of a maximum bet/raise
            #bluffing
            # if beta==0.7:

            # #if round is preflop
            if street==1:
                if random.random() < phi:
                    return RaiseAction(min(min_raise + (gamma * opp_pip - min_raise) * random.random(), max_raise))
                else:
                    return CallAction()
            #if round is not preflop
            else:
                if random.random() < beta:
                    return RaiseAction(min(min_raise + (gamma * opp_pip - min_raise) * random.random(), max_raise))
                else:
                    return CallAction()

        return CallAction()






if __name__ == '__main__':
    run_bot(Player(), parse_args())
