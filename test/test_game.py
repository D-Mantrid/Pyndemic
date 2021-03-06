import unittest
from unittest import TestCase

import os.path as op
import random

from pyndemic.exceptions import *
from pyndemic.deck import PlayerDeck, InfectDeck
from pyndemic.game import Game
from pyndemic.character import Character
from .test_helpers import MockController


class GameSetupTestCase(TestCase):
    def setUp(self):
        self.controller = MockController()
        self._ctx = self.controller._ctx

        self.pg = Game()
        self.controller.game = self.pg
        self.settings = self.controller.settings

        self.pg.settings = self.settings

    def tearDown(self):
        del self.controller

    def test_add_character(self):
        characters = [Character('Evie'), Character('Amelia')]

        for character in characters:
            self.pg.add_character(character)

            with self.subTest(character=character):
                self.assertIs(self.pg, character.game)
                self.assertIn(character, self.pg.characters)
                self.assertEqual(character.name, self.pg.characters[-1].name)

    def test_get_infection_rate(self):
        self.pg.get_infection_rate()
        self.assertEqual(2, self.pg.infection_rate)

    def test_get_new_city_map(self):
        self.pg.get_new_city_map()

        self.assertEqual(40, len(self.pg.city_map))
        self.assertIn('London', self.pg.city_map)

        city = self.pg.city_map['London']
        self.assertEqual('London', city.name)
        self.assertEqual('Blue', city.colour)
        self.assertEqual('Yellow', self.pg.city_map['Washington'].colour)

        self.assertEqual(6, len(city.connected_cities))
        self.assertIn(self.pg.city_map['Washington'], city.connected_cities)
        self.assertNotIn(self.pg.city_map['Liverpool'], city.connected_cities)

    def test_create_cities(self):
        self.pg.create_cities()

        self.assertEqual(40, len(self.pg.city_map))
        self.assertIn('London', self.pg.city_map)

        city = self.pg.city_map['London']
        self.assertEqual('London', city.name)
        self.assertEqual('Blue', city.colour)
        self.assertEqual('Yellow', self.pg.city_map['Washington'].colour)

    def test_connect_cities(self):
        self.pg.create_cities()
        self.pg.connect_cities()
        city = self.pg.city_map['London']

        self.assertEqual(6, len(city.connected_cities))
        self.assertIn(self.pg.city_map['Washington'], city.connected_cities)
        self.assertNotIn(self.pg.city_map['Liverpool'], city.connected_cities)

    def test_get_new_decks(self):
        self.pg.player_deck = PlayerDeck()
        self.pg.infect_deck = InfectDeck()

        self.pg.get_new_city_map()
        self.pg.get_new_decks()

        deck = self.pg.player_deck
        self.assertEqual('London', deck.cards[0].name)
        self.assertEqual('Black', deck.cards[29].colour)

        deck = self.pg.infect_deck
        self.assertEqual('London', deck.cards[0].name)
        self.assertEqual('Black', deck.cards[29].colour)

    def test_get_new_diseases(self):
        self.pg.get_new_diseases()

        self.assertEqual('Red', self.pg.diseases['Red'].colour)
        self.assertEqual(30, self.pg.diseases['Blue'].public_health)

    def test_set_starting_epidemics(self):
        self.pg.set_starting_epidemics()
        self.assertEqual(4, self.pg.starting_epidemics)

    def test_setup_game(self):
        del self.pg.settings

        characters = [Character('Evie'), Character('Amelia')]
        for character in characters:
            self.pg.add_character(character)

        self.pg.setup_game(self.settings)

        self.assertEqual(self.pg.settings, self.settings)

        self.assertEqual(0, self.pg.epidemic_count)
        self.assertEqual(0, self.pg.outbreak_count)
        self.assertFalse(self.pg.game_won)
        self.assertFalse(self.pg.game_over)

        self.assertEqual(2, self.pg.infection_rate)

        self.assertIn('New York', self.pg.city_map)
        self.newyork = self.pg.city_map['New York']
        self.assertEqual('New York', self.newyork.name)
        self.assertEqual('Yellow', self.newyork.colour)
        self.assertEqual(3, len(self.newyork.connected_cities))
        for colour in ('Blue', 'Red', 'Yellow', 'Black'):
            self.assertIn(colour, self.newyork.infection_levels)

        top_player_card = self.pg.player_deck.take_top_card()
        top_infect_card = self.pg.infect_deck.take_top_card()
        self.assertEqual('London', top_player_card.name)
        self.assertEqual('London', top_infect_card.name)

        self.assertEqual('Red', self.pg.diseases['Red'].colour)
        self.assertEqual(30, self.pg.diseases['Black'].public_health)

        self.assertEqual(4, self.pg.starting_epidemics)


class GameTestCase(unittest.TestCase):

    def setUp(self):
        self.controller = MockController()
        self._ctx = self.controller._ctx
        self.settings = self.controller.settings

        random.seed(42)
        self.character1 = Character('Evie')
        self.character2 = Character('Amelia')
        self.pg = Game()
        self.pg.add_character(self.character1)
        self.pg.add_character(self.character2)

        self.controller.game = self.pg
        self.pg.setup_game(self.settings)

    def tearDown(self):
        del self.controller

    def test_all_one_colour(self):
        card_names = ['London', 'Oxford', 'Cambridge', 'Brighton', 'Southampton']
        self.assertTrue(self.pg.all_one_colour(card_names))

        card_names[3] = 'Moscow'
        self.assertFalse(self.pg.all_one_colour(card_names))

    def test_all_diseases_cured(self):
        self.assertFalse(self.pg.all_diseases_cured())

        self.pg.diseases['Yellow'].cured = True
        self.assertFalse(self.pg.all_diseases_cured())

        self.pg.diseases['Blue'].cured = True
        self.pg.diseases['Black'].cured = True
        self.assertFalse(self.pg.all_diseases_cured())

        self.pg.diseases['Red'].cured = True
        self.assertTrue(self.pg.all_diseases_cured())

    def test_add_epidemics(self):
        self.pg.add_epidemics()
        num_epidemics = len({card for card in self.pg.player_deck.cards
                             if card.name == 'Epidemic'})
        self.assertTrue(self.pg.starting_epidemics, num_epidemics)

    def test_infect_city(self):
        self.pg.infect_city('London', 'Blue')
        self.assertEqual(1, self.pg.city_map['London'].infection_levels['Blue'])

        self.pg.diseases['Blue'].public_health = 0
        with self.assertRaises(GameCrisisException):
            self.pg.infect_city('London', 'Blue')

    def test_infect_city_phase(self):
        self.pg.infect_city_phase()
        self.assertEqual(1, self.pg.city_map['London'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Oxford'].infection_levels['Blue'])
        self.assertEqual(2, len(self.pg.infect_deck.discard))
        self.assertEqual('London', self.pg.infect_deck.discard[0].name)
        self.assertEqual(28, self.pg.diseases['Blue'].public_health)

        self.pg.infect_city('London', 'Blue')
        self.assertEqual(0, len(self.pg.outbreak_stack))

    def test_skipping_infect_city_phase(self):
        self.pg.skip_infect_phase = True
        self.pg.infect_city_phase()
        self.assertEqual(0, self.pg.city_map['London'].infection_levels['Blue'])

    def test_infect_city_phase_ouitbreak_stack(self):
        """Tests that the outbreak stack is cleaned after each drawn card.
        This reflects in how many cities are infected and how much.
        """
        london = self.pg.city_map['London']
        oxford = self.pg.city_map['Oxford']
        london.infection_levels['Blue'] = 3
        oxford.infection_levels['Blue'] = 3

        self.pg.infect_city_phase()
        self.assertEqual(6, self.pg.outbreak_count)
        self.assertEqual(10, self.pg.diseases['Blue'].public_health)
        self.assertEqual(2, self.pg.city_map['Bristol'].infection_levels['Blue'])
        self.assertEqual(3, self.pg.city_map['Cambridge'].infection_levels['Blue'])

    def test_epidemic_phase(self):
        self.pg.epidemic_phase()
        self.assertEqual(3, self.pg.city_map['Belgorod'].infection_levels['Black'])
        top_infect_card = self.pg.infect_deck.take_top_card()
        self.assertEqual('Belgorod', top_infect_card.name)
        self.assertEqual('Black', top_infect_card.colour)
        self.assertEqual(1, self.pg.epidemic_count)
        self.assertEqual(0, len(self.pg.infect_deck.discard))

    def test_outbreak_trigger(self):
        for i in range(4):
            self.pg.infect_city('London', 'Blue')
        self.assertEqual(3, self.pg.city_map['London'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Oxford'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Cambridge'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Brighton'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Washington'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Bejing'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Moscow'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.outbreak_count)

    def test_outbreak(self):
        self.pg.outbreak('London', 'Blue')
        self.assertEqual(1, self.pg.city_map['Oxford'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Cambridge'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Brighton'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Washington'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Bejing'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Moscow'].infection_levels['Blue'])

        self.pg.outbreak_count = 7
        self.pg.outbreak_stack.clear()
        with self.assertRaises(GameCrisisException):
            self.pg.outbreak('London', 'Blue')

    def test_shuffle(self):
        self.assertEqual('London', self.pg.player_deck.take_top_card().name)
        self.pg.player_deck.shuffle()
        self.assertNotEqual('Oxford', self.pg.player_deck.take_top_card().name)

        self.assertEqual('London', self.pg.infect_deck.take_top_card().name)
        self.pg.infect_deck.shuffle()
        self.assertNotEqual('Oxford', self.pg.infect_deck.take_top_card().name)

    def test_start_game(self):
        self.pg.start_game()
        self.top_player_card = self.pg.player_deck.take_top_card()
        self.top_infect_card = self.pg.infect_deck.take_top_card()
        self.assertEqual(9, len(self.pg.infect_deck.discard))
        self.assertEqual(0, len(self.pg.player_deck.discard))
        self.assertEqual(3, self.pg.city_map['Brighton'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Detroit'].infection_levels['Yellow'])
        self.assertEqual(2, self.pg.city_map['Smolensk'].infection_levels['Black'])
        self.assertEqual(4, len(self.character1.hand))
        self.assertEqual(4, len(self.character2.hand))
        self.assertNotEqual('London', self.top_player_card.name)
        self.assertNotEqual('London', self.top_infect_card.name)
        self.assertEqual('London', self.pg.characters[0].location.name)
        self.assertEqual('London', self.pg.characters[1].location.name)
        self.assertTrue(self.pg.city_map['London'].has_lab)

        for i in range(10):
            self.pg.player_deck.draw_card(self.character1)
        self.assertEqual(1, self.pg.epidemic_count)

    def test_initial_infect_phase(self):
        self.pg.initial_infect_phase()
        self.assertEqual(3, self.pg.city_map['London'].infection_levels['Blue'])
        self.assertEqual(3, self.pg.city_map['Oxford'].infection_levels['Blue'])
        self.assertEqual(3, self.pg.city_map['Cambridge'].infection_levels['Blue'])
        self.assertEqual(2, self.pg.city_map['Brighton'].infection_levels['Blue'])
        self.assertEqual(2, self.pg.city_map['Southampton'].infection_levels['Blue'])
        self.assertEqual(2, self.pg.city_map['Bristol'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Plymouth'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Liverpool'].infection_levels['Blue'])
        self.assertEqual(1, self.pg.city_map['Manchester'].infection_levels['Blue'])
        self.assertEqual(9, len(self.pg.infect_deck.discard))
        self.assertEqual(12, self.pg.diseases['Blue'].public_health)

    def test_draw_initial_hands(self):
        test_cards = self.pg.player_deck.cards[:8]
        self.pg.draw_initial_hands()

        for i, character in enumerate(self.pg.characters):
            with self.subTest(i=i, character=character):
                self.assertEqual(4, len(character.hand))
                self.assertEqual(test_cards[i * 4 + 3].name, character.hand[3].name)

    def test_get_new_disease(self):
        self.assertFalse(self.pg.diseases['Blue'].cured)
        self.assertFalse(self.pg.diseases['Red'].cured)
        self.pg.diseases['Blue'].cured = True
        self.assertTrue(self.pg.diseases['Blue'].cured)


if __name__ == '__main__':
    unittest.main()
