"""
Web-based visualization server for Pokerbots game engine.
Run this instead of engine.py to see the game in a web browser.
"""
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import queue
import time

# Import engine components
import sys
import os
sys.path.append(os.getcwd())

from engine import Game, Player, RoundState, TerminalState, FoldAction, CallAction, CheckAction, RaiseAction, DiscardAction
from config import PLAYER_1_NAME, PLAYER_1_PATH, PLAYER_2_NAME, PLAYER_2_PATH, NUM_ROUNDS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pokerbots-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
game_running = False
game_thread = None
current_round_state = None
current_active_player = None
waiting_for_human_action = False
player_action_queues = {}

STREET_NAMES = ['Pre-flop', 'Flop', 'Discard 1', 'Discard 2', 'Turn', 'River']

def format_card(card_obj):
    """Format card object or string for display"""
    if not card_obj:
        return None
    
    # Convert Card object to string if needed
    if not isinstance(card_obj, str):
        card_str = str(card_obj)
    else:
        card_str = card_obj
    
    if len(card_str) < 2:
        return None
    
    rank = card_str[0]
    suit = card_str[1]
    suit_symbols = {'h': '♥', 'd': '♦', 's': '♠', 'c': '♣'}
    suit_colors = {'h': 'red', 'd': 'red', 's': 'black', 'c': 'black'}
    return {
        'rank': rank,
        'suit': suit_symbols.get(suit, suit),
        'color': suit_colors.get(suit, 'black'),
        'raw': card_str
    }

def get_game_state_dict(round_state, players, active_player_index, street_name):
    """Convert game state to dictionary for JSON serialization"""
    # Handle None players gracefully
    player_names = ['Player A', 'Player B']
    bankrolls = [0, 0]
    if players and len(players) >= 2:
        if players[0] is not None:
            player_names[0] = players[0].name
            bankrolls[0] = players[0].bankroll
        if players[1] is not None:
            player_names[1] = players[1].name
            bankrolls[1] = players[1].bankroll
    elif players and len(players) >= 1 and players[0] is not None:
        player_names[0] = players[0].name
        bankrolls[0] = players[0].bankroll
    
    if isinstance(round_state, TerminalState):
        prev_state = round_state.previous_state
        return {
            'type': 'terminal',
            'deltas': round_state.deltas,
            'hands': [
                [format_card(c) for c in prev_state.hands[0]],
                [format_card(c) for c in prev_state.hands[1]]
            ],
            'board': [format_card(c) for c in prev_state.board],
            'stacks': prev_state.stacks,
            'pips': prev_state.pips,
            'player_names': player_names,
            'bankrolls': bankrolls,
        }
    
    return {
        'type': 'round',
        'street': round_state.street,
        'street_name': street_name,
        'hands': [
            [format_card(c) for c in round_state.hands[0]],
            [format_card(c) for c in round_state.hands[1]]
        ],
        'board': [format_card(c) for c in round_state.board],
        'stacks': round_state.stacks,
        'pips': round_state.pips,
        'active_player': active_player_index,
        'player_names': player_names,
        'bankrolls': bankrolls,
    }

class WebGame(Game):
    """Extended Game class that broadcasts state to web clients"""
    
    def __init__(self):
        super().__init__()
        self.players = None
        self.current_round_state = None
        
    def log_round_state(self, players, round_state):
        """Override to broadcast state"""
        super().log_round_state(players, round_state)
        self.current_round_state = round_state
        self.players = players
        
        active = round_state.button % 2
        street_idx = round_state.street if round_state.street < len(STREET_NAMES) else round_state.street - 2
        street_name = STREET_NAMES[street_idx] if street_idx < len(STREET_NAMES) else f"Street {round_state.street}"
        
        state_dict = get_game_state_dict(round_state, players, active, street_name)
        try:
            socketio.emit('game_state', state_dict)
        except Exception as e:
            print(f"Error emitting game_state: {e}")
        
    def log_action(self, name, action, bet_override, hand):
        """Override to broadcast actions"""
        super().log_action(name, action, bet_override, hand)
        
        action_dict = {
            'player': name,
            'action': action.__class__.__name__,
            'details': {}
        }
        
        if isinstance(action, RaiseAction):
            action_dict['details'] = {'amount': action.amount}
        elif isinstance(action, DiscardAction):
            action_dict['details'] = {'card_index': action.card, 'card': str(hand[action.card]) if hand and action.card < len(hand) else ''}
        
        try:
            socketio.emit('action', action_dict)
        except Exception as e:
            print(f"Error emitting action: {e}")
        
    def log_terminal_state(self, players, round_state):
        """Override to broadcast terminal state"""
        super().log_terminal_state(players, round_state)
        
        state_dict = get_game_state_dict(round_state, players, 0, "Showdown")
        try:
            socketio.emit('game_state', state_dict)
            socketio.emit('round_end', {'deltas': round_state.deltas})
        except Exception as e:
            print(f"Error emitting terminal state: {e}")

class WebPlayer(Player):
    """Extended Player class that can accept actions from web interface"""
    
    def __init__(self, name, path):
        super().__init__(name, path)
        self.is_chatbot = ("player_chatbot" in path)
        self.web_action_queue = queue.Queue() if self.is_chatbot else None
        if self.is_chatbot:
            player_action_queues[name] = self.web_action_queue
        
    def query(self, round_state, player_message, game_log):
        """Override to check for web actions when chatbot is active"""
        global waiting_for_human_action, current_round_state, current_active_player
        
        if self.is_chatbot and self.web_action_queue:
            # Check if we're waiting for human action
            waiting_for_human_action = True
            current_round_state = round_state
            current_active_player = self
            
            # Emit request for action to web clients
            legal_actions = round_state.legal_actions() if isinstance(round_state, RoundState) else {CheckAction}
            legal_actions_list = [action.__name__ for action in legal_actions]
            
            socketio.emit('request_action', {
                'player': self.name,
                'legal_actions': legal_actions_list,
                'round_state': get_game_state_dict(round_state, [self, None], 0, "Current")
            })
            
            # Wait for action from web interface (with timeout)
            try:
                action_data = self.web_action_queue.get(timeout=120)  # 2 minute timeout
                waiting_for_human_action = False
                
                # Convert action data to action object
                action_type = action_data.get('action')
                if action_type == 'Fold':
                    return FoldAction()
                elif action_type == 'Call':
                    return CallAction()
                elif action_type == 'Check':
                    return CheckAction()
                elif action_type == 'Raise':
                    amount = action_data.get('amount')
                    return RaiseAction(amount)
                elif action_type == 'Discard':
                    card_index = action_data.get('card_index')
                    return DiscardAction(card_index)
            except queue.Empty:
                waiting_for_human_action = False
                return CheckAction() if CheckAction in legal_actions else FoldAction()
        
        # Fall back to normal query
        return super().query(round_state, player_message, game_log)

def run_game():
    """Run the game in a separate thread"""
    global game_running, waiting_for_human_action
    
    try:
        game_running = True
        waiting_for_human_action = False
        
        socketio.emit('game_start', {'message': 'Game starting...'})
        socketio.sleep(0.1)  # Give time for message to send
        
        game = WebGame()
        players = [
            WebPlayer(PLAYER_1_NAME, PLAYER_1_PATH),
            WebPlayer(PLAYER_2_NAME, PLAYER_2_PATH)
        ]
        
        socketio.emit('status_update', {'message': 'Building players...'})
        socketio.sleep(0.1)
        
        for player in players:
            try:
                player.build()
            except Exception as e:
                socketio.emit('error', {'message': f'Error building {player.name}: {str(e)}'})
                raise
        
        socketio.emit('status_update', {'message': 'Starting player connections...'})
        socketio.sleep(0.1)
        
        for player in players:
            try:
                player.run()
                if player.socketfile is None:
                    raise Exception(f'Failed to connect {player.name}')
            except Exception as e:
                socketio.emit('error', {'message': f'Error running {player.name}: {str(e)}'})
                raise
        
        socketio.emit('status_update', {'message': 'Game ready, starting rounds...'})
        socketio.sleep(0.1)
        
        for round_num in range(1, NUM_ROUNDS + 1):
            socketio.emit('round_start', {'round': round_num})
            socketio.sleep(0.1)
            game.run_round(players)
            players = players[::-1]
            
            # Small delay for visualization
            socketio.sleep(0.5)
        
        socketio.emit('game_end', {'message': 'Game finished'})
        
        for player in players:
            try:
                player.stop()
            except:
                pass
        
        game_running = False
    except Exception as e:
        import traceback
        error_msg = f'Game error: {str(e)}\n{traceback.format_exc()}'
        socketio.emit('error', {'message': error_msg})
        print(error_msg)
        game_running = False

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to Pokerbots server'})

@socketio.on('start_game')
def handle_start_game():
    """Start the game when requested"""
    global game_thread, game_running
    
    if not game_running and (game_thread is None or not game_thread.is_alive()):
        game_thread = threading.Thread(target=run_game, daemon=True)
        game_thread.start()
        emit('game_started', {'message': 'Game thread started'})

@socketio.on('player_action')
def handle_player_action(data):
    """Handle action from web interface"""
    global waiting_for_human_action, current_active_player
    
    player_name = data.get('player', PLAYER_1_NAME)
    if player_name in player_action_queues:
        queue_obj = player_action_queues[player_name]
        queue_obj.put(data)
        emit('action_received', {'message': 'Action received'})
    else:
        emit('action_error', {'message': 'Not waiting for action or invalid player'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    pass

if __name__ == '__main__':
    print("Starting Pokerbots Web Server...")
    print("Open http://localhost:5000 in your browser")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
