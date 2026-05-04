"""Shared constants for the astrology engine."""

SIGN_NAMES = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

NAKSHATRA_NAMES = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashirsha",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

VIMSHOTTARI_SEQUENCE = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

PLANET_ORDER = [
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
]

PLANETARY_LORDSHIPS = {
    "Sun": [4],
    "Moon": [3],
    "Mars": [0, 7],
    "Mercury": [2, 5],
    "Jupiter": [8, 11],
    "Venus": [1, 6],
    "Saturn": [9, 10],
    "Rahu": [],
    "Ketu": [],
}

EXALTATION_SIGNS = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 9,
    "Mercury": 5,
    "Jupiter": 3,
    "Venus": 11,
    "Saturn": 6,
    "Rahu": 2,
    "Ketu": 8,
}

DEBILITATION_SIGNS = {
    "Sun": 6,
    "Moon": 7,
    "Mars": 3,
    "Mercury": 11,
    "Jupiter": 9,
    "Venus": 5,
    "Saturn": 0,
    "Rahu": 8,
    "Ketu": 2,
}

MOOLATRIKONA_SIGNS = {
    "Sun": 4,
    "Moon": 2,
    "Mars": 0,
    "Mercury": 5,
    "Jupiter": 8,
    "Venus": 6,
    "Saturn": 10,
    "Rahu": 10,
    "Ketu": 8,
}

PLANET_FRIENDS = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "enemies": {"Venus", "Saturn"}, "neutral": {"Mercury"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "enemies": set(), "neutral": {"Mars", "Jupiter", "Venus", "Saturn"}},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "enemies": {"Mercury"}, "neutral": {"Venus", "Saturn"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "enemies": {"Moon"}, "neutral": {"Mars", "Jupiter", "Saturn"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "enemies": {"Venus", "Mercury"}, "neutral": {"Saturn"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "enemies": {"Sun", "Moon"}, "neutral": {"Mars", "Jupiter"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "enemies": {"Sun", "Moon", "Mars"}, "neutral": {"Jupiter"}},
    "Rahu": {"friends": {"Venus", "Saturn", "Mercury"}, "enemies": {"Sun", "Moon"}, "neutral": {"Mars", "Jupiter", "Ketu"}},
    "Ketu": {"friends": {"Mars", "Jupiter", "Venus"}, "enemies": {"Sun", "Moon"}, "neutral": {"Mercury", "Saturn", "Rahu"}},
}

COMBUSTION_ORBS = {
    "Moon": 12.0,
    "Mercury": 14.0,
    "Venus": 10.0,
    "Mars": 17.0,
    "Jupiter": 11.0,
    "Saturn": 15.0,
    "Rahu": 10.0,
    "Ketu": 10.0,
}

VEDIC_ASPECTS = {
    "Sun": [7],
    "Moon": [7],
    "Mars": [4, 7, 8],
    "Mercury": [7],
    "Jupiter": [5, 7, 9],
    "Venus": [7],
    "Saturn": [3, 7, 10],
    "Rahu": [5, 7, 9],
    "Ketu": [5, 7, 9],
}

PLANET_TO_SWE_NAME = {
    "Sun": "SUN",
    "Moon": "MOON",
    "Mars": "MARS",
    "Mercury": "MERCURY",
    "Jupiter": "JUPITER",
    "Venus": "VENUS",
    "Saturn": "SATURN",
    "Rahu": "MEAN_NODE",
}

