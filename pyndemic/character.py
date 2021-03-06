import logging

from .exceptions import GameCrisisException
from .core import GameEntity


class LastDiseaseCuredException(GameCrisisException):
    def __str__(self):
        return 'All diseases have been cured!'


class Character(GameEntity):
    def __init__(self, name):
        self.game = None
        self.location = None
        self.action_count = 0
        self.hand = []
        self.name = name
        logging.debug(
            f'Created {self}')

    def __str__(self):
        return f'Character "{self.name}"'

    def info(self):
        result = f'Character {self.name}'
        if self.location is not None:
            result += f' (stays at: {self.location.name}).'

        return result

    def get_card(self, card_name):
        for card in self.hand:
            if card.name == card_name:
                return card
        raise ValueError(
            f"No such card in {self.name} character's hand: {card_name}.")

    def set_location(self, new_location):
        self.location = self.game.city_map[new_location]
        logging.debug(
            f'{self}: changed location to {new_location}.')

    def check_charter_flight(self, location):
        if self.action_count > 0 and self.location.name == location:
            if self.hand_contains(location):
                return True
        return False

    def charter_flight(self, location, destination):
        if self.check_charter_flight(location):
            self.discard_card(location)
            self.set_location(destination)
            self.action_count -= 1
            self.emit_signal(
                (f'{self}: Performed charter flight from {location} to '
                 f'{destination}.'),
            )
            return True
        return False

    def check_direct_flight(self, location, destination):
        if self.action_count > 0 and self.location.name == location:
            if self.hand_contains(destination):
                return True
        return False

    def direct_flight(self, location, destination):
        if self.check_direct_flight(location, destination):
            self.discard_card(destination)
            self.set_location(destination)
            self.action_count -= 1
            self.emit_signal(
                (f'{self}: Performed direct flight from {location} to '
                 f'{destination}.'),
            )
            return True
        return False

    def check_build_lab(self):
        if self.action_count > 0 and not self.location.has_lab:
            if self.hand_contains(self.location.name):
                return True
        return False

    def build_lab(self):
        if self.check_build_lab():
            self.discard_card(self.location.name)
            self.location.build_lab()
            self.action_count -= 1
            self.emit_signal(
                f'{self}: Built laboratory in {self.location}.',
            )
            return True
        return False

    def check_shuttle_flight(self, location, destination):
        if self.action_count > 0 and self.location.name == location:
            if self.location.has_lab and \
                    self.game.city_map.get(destination).has_lab:
                return True
        return False

    def shuttle_flight(self, location, destination):
        if self.check_shuttle_flight(location, destination):
            self.set_location(destination)
            self.action_count -= 1
            self.emit_signal(
                (f'{self}: Performed shuttle flight from {location} to '
                 f'{destination}.'),
            )
            return True
        return False

    def check_treat_disease(self, colour):
        if self.action_count > 0:
            if self.location.infection_levels.get(colour, 0) > 0:
                return True
        return False

    def treat_disease(self, colour):
        if self.check_treat_disease(colour):
            if self.game.diseases[colour].cured:
                level_reduction = self.location.nullify_infection_level(colour)
                self.game.diseases[colour].increase_resistance(level_reduction)
                self.emit_signal(
                    (f'{self}: Treated {colour} disease in {self.location} '
                     f'(effectively).'),
                )
            else:
                self.location.decrease_infection_level(colour)
                self.game.diseases[colour].increase_resistance(1)
                self.emit_signal(
                    f'{self}: Treated {colour} disease in {self.location}.',
                    log_level=logging.INFO)
            self.action_count -= 1
            self.emit_signal(
                (f'Now {self.location} has '
                 f'{self.location.infection_levels[colour]} '
                 f'level of {colour} disease.'),
            )

            return True
        return False

    def check_cure_disease(self, card1, card2, card3, card4, card5):
        card_list = [card1, card2, card3, card4, card5]
        if len(set(card_list)) != 5:
            return False
        if self.action_count > 0 and self.location.has_lab:
            all_one_colour = self.game.all_one_colour(card_list)
            all_in_hand = all(self.hand_contains(card) for card in card_list)
            if all_in_hand and all_one_colour:
                return True
        return False

    def cure_disease(self, card1, card2, card3, card4, card5):
        if self.check_cure_disease(card1, card2, card3, card4, card5):
            colour = self.get_card(card1).colour
            self.game.diseases[colour].cured = True
            card_list = [card1, card2, card3, card4, card5]
            for card in card_list:
                self.discard_card(card)
            self.action_count -= 1
            self.emit_signal(
                f'{self}: Cured {colour} disease in {self.location}.',
            )

            if self.game.all_diseases_cured():
                raise LastDiseaseCuredException

            return True
        return False

    def check_share_knowledge(self, card_name, other_character):
        if other_character is self:
            return False

        no_actions = self.action_count == 0
        different_locations = self.location.name != other_character.location.name
        card_mismatch = card_name != other_character.location.name
        if no_actions or different_locations or card_mismatch:
            return False

        if self.hand_contains(card_name) or other_character.hand_contains(card_name):
            return True
        return False

    def share_knowledge(self, card_name, other_character):
        if self.check_share_knowledge(card_name, other_character):
            transfer_forward = True
            try:
                held_card = self.get_card(card_name)
            except ValueError:
                held_card = other_character.get_card(card_name)
                transfer_forward = False
            if transfer_forward:
                other_character.add_card(held_card)
                self.hand.remove(held_card)
            else:
                self.add_card(held_card)
                other_character.hand.remove(held_card)
            self.action_count -= 1
            self.emit_signal(
                f'{self}: Shared knowledge {held_card} with {other_character}.',
            )

            return True
        return False

    def add_card(self, new_card):
        self.hand.append(new_card)
        logging.debug(
            f'{self}: Received new {new_card}.')

    def discard_card(self, to_discard):
        if self.hand_contains(to_discard):
            card_to_discard = self.get_card(to_discard)
            self.hand.remove(card_to_discard)
            self.game.player_deck.add_discard(card_to_discard)
            self.emit_signal(
                f'{self}: discarded {card_to_discard}.',
            )

            return True
        return False

    def hand_contains(self, card_name):
        return any(card.name == card_name for card in self.hand)

    def check_standard_move(self, location, destination):
        if self.action_count > 0 and self.location.name == location:
            destination_city = self.game.city_map[destination]
            if destination_city in self.location.connected_cities:
                return True
        return False

    def standard_move(self, location, destination):
        if self.check_standard_move(location, destination):
            self.set_location(destination)
            self.action_count -= 1
            self.emit_signal(
                (f'{self}: Performed standard move from {location} to '
                 f'{destination}.'),
            )

            return True
        return False

    def check_action_card(self, card_name, *args):
        card = self.get_card(card_name)
        return card.check_playable(*args)

    def play_action_card(self, card_name, *args):
        if self.check_action_card(card_name, *args):
            self.emit_signal(
                f'{self}: Playing {card_name}.')
            card = self.get_card(card_name)
            card.on_play(*args)
            #TODO check if fails
            self.discard_card(card_name)
            return True
        return False
