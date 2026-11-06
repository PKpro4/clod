from .base import Game
from .riddles import CodeRiddles
from .trivia import Trivia
from .twenty_questions import TwentyQuestions

GAMES: dict[str, type[Game]] = {
    TwentyQuestions.key: TwentyQuestions,
    Trivia.key: Trivia,
    CodeRiddles.key: CodeRiddles,
}

__all__ = ["GAMES", "Game", "TwentyQuestions", "Trivia", "CodeRiddles"]
