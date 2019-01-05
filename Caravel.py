#!/usr/bin/env python3
# Python 3.6

import hlt # Halite SDK
from hlt import constants # Constants values
from hlt.positionals import Direction

import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("Caravel")

logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {}

while True:
    game.update_frame()
    me = game.me # Player metadata
    game_map = game.game_map # Map metadata

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    # end of the turn.
    command_queue = []

    # The positions occupied by each ship on the next turn.
    next_positions = []

    # If we call a get_surrounding_cardinals(), the directions
    # are given in this order
    directions = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

    for ship in me.get_ships():
        if ship.id in ship_status:
            logging.info("Ship " + str(ship.id) + " - " + str(ship_status[ship.id]))

        if ship.id not in ship_status:
            ship_status[ship.id] = "exploring"

        elif game.turn_number > constants.MAX_TURNS - (constants.MAX_TURNS / 20):
            ship_status[ship.id] = "shutdown"

        elif ship.halite_amount >= 3 * (constants.MAX_HALITE / 4):
            logging.info("Ship {} will return to base.".format(ship.id))
            ship_status[ship.id] = "returning"
        
        if ship_status[ship.id] == "returning":
            logging.info("Ship {} returning...".format(ship.id))
            if ship.position == me.shipyard.position:
                ship_status[ship.id] = "exploring"
            else:
                move = game_map.naive_navigate(ship, me.shipyard.position)
                logging.info(ship.position.directional_offset(move))
                if ship.position.directional_offset(move) not in next_positions:
                    next_positions.append(ship.position.directional_offset(move))
                    command_queue.append(ship.move(move))
                else:
                    next_positions.append(ship.position)
                continue

        elif ship_status[ship.id] == "exploring":
            # We check how many halite there is in the current and
            # surrounding positions and move to the one with the most
            position_options = ship.position.get_surrounding_cardinals() + [ship.position]

            position_dict = {} # {(0,1): Position(x,y), (etc)}
            halite_dict = {} # {(0,1): 423, (etc)}

            for n in range(5):
                position_dict[directions[n]] = position_options[n]
                halite_dict[directions[n]] = game_map[position_options[n]].halite_amount

            logging.info(position_dict)
            logging.info(halite_dict)
        
            # Finding the key with the maximum value
            move_choice = max(halite_dict, key=halite_dict.get)
            position_choice = position_dict[move_choice]

            if position_choice not in next_positions and game_map[position_choice].is_occupied == False and (ship.halite_amount >= game_map[ship.position].halite_amount / 10):
                logging.info("Ship {} moving to {}.".format(ship.id, move_choice))
                command_queue.append(ship.move(move_choice))
                next_positions.append(position_choice)
            else:
                command_queue.append(ship.stay_still())
                next_positions.append(ship.position)
            continue

        elif ship_status[ship.id] == "shutdown":
            # If the ship status is shutdown, we just want to get it back
            # to the shipyard. If the ship is about to move to the shipyard
            # but it's already occupied, move anyway. The halite resulting
            # of the collision should drop in the shipyard anyway.
            move = game_map.naive_navigate(ship, me.shipyard.position)
            logging.info(ship.position.directional_offset(move))
            if ship.position.directional_offset(move) not in next_positions:
                next_positions.append(ship.position.directional_offset(move))
                command_queue.append(ship.move(move))
            elif ship.position.directional_offset(move) in next_positions and ship.position.directional_offset(move) == me.shipyard.position:
                command_queue.append(ship.move(move))
            else:
                next_positions.append(ship.position)
            continue

    ##
    ## TODO: stop making ships after a certain round.
    ## Make any round related behaviour account for game size.
    ##
    if game.turn_number <= constants.MAX_TURNS / 4 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())
    elif (game.turn_number > constants.MAX_TURNS and game.turn_number < constants.MAX_TURNS - (constants.MAX_TURNS / 10)) and me.halite_amount >= (constants.SHIP_COST * 3) and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)