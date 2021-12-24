# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random


def get_random_quote():
	quotes = [
		("Start by doing what's necessary; then do what's possible; and suddenly you are doing the impossible.", "Francis of Assisi"),
		("The best and most beautiful things in the world cannot be seen or even touched - they must be felt with the heart.", "Hellen Keller"),
		("I can't change the direction of the wind, but I can adjust my sails to always reach my destination.", "Jimmy Dean"),
		("We know what we are, but know not what we may be.", "William Shakespeare"),
		("There are only two mistakes one can make along the road to truth; not going all the way, and not starting.", "Buddha"),
		("Always remember that you are absolutely unique. Just like everyone else.", "Margaret Mead"),
		("You have to learn the rules of the game. And then you have to play better than anyone else.", "Albert Einstein"),
		("Once we accept our limits, we go beyond them.", "Albert Einstein"),
		("Quality is not an act, it is a habit.", "Aristotle"),
		("The more that you read, the more things you will know. The more that you learn, the more places you'll go.", "Dr. Seuss"),
		("From there to here, and here to there, funny things are everywhere.", "Dr. Seuss"),
		("The secret of getting ahead is getting started.", "Mark Twain"),
		("All generalizations are false, including this one.", "Mark Twain"),
		("Don't let schooling interfere with your education.", "Mark Twain"),
		("Cauliflower is nothing but cabbage with a college education.", "Mark Twain"),
		("It's not the size of the dog in the fight, it's the size of the fight in the dog.", "Mark Twain"),
		("Climate is what we expect, weather is what we get.", "Mark Twain"),
		("There are lies, damned lies and statistics.", "Mark Twain"),
		("Happiness is when what you think, what you say, and what you do are in harmony.", "Mahatma Gandhi"),
		("First they ignore you, then they laugh at you, then they fight you, then you win.", "Mahatma Gandhi"),
		("There is more to life than increasing its speed.", "Mahatma Gandhi"),
		("A small body of determined spirits fired by an unquenchable faith in their mission can alter the course of history.", "Mahatma Gandhi"),
		("If two wrongs don't make a right, try three.", "Laurence J. Peter"),
		("Inspiration exists, but it has to find you working.", "Pablo Picasso"),
		("The world’s first speeding ticket was given to a man going 4 times the speed limit! Walter Arnold was traveling at a breakneck 8 miles an hour in a 2mph zone, and was caught by a policeman on bicycle and fined one shilling!"),
	]

	return random.choice(quotes)
