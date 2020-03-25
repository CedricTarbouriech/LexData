import json
import logging
from typing import Dict, List

from .entity import Entity
from .form import Form
from .language import Language
from .sense import Sense
from .wikidatasession import WikidataSession


class Lexeme(Entity):
    """Wrapper around a dict to represent a Lexeme"""

    def __init__(self, repo: WikidataSession, idLex: str):
        super().__init__()
        self.repo = repo
        self.getLex(idLex)

    def getLex(self, idLex: str):
        """this function gets and returns the data of a lexeme for a given id

        :param idLex: Lexeme identifier (example: "L2")
        :type  idLex: str
        :returns: Simplified object representation of Lexeme

        """

        PARAMS = {"action": "wbgetentities", "format": "json", "ids": idLex}

        DATA = self.repo.get(PARAMS)

        self.update(DATA["entities"][idLex])

    @property
    def lemma(self) -> str:
        """
        the lemma of the lexeme as string

        :rtype: str
        """
        return list(self["lemmas"].values())[0]["value"]

    @property
    def language(self) -> str:
        """
        the language code of the lexeme as string

        :rtype: str
        """
        return list(self["lemmas"].values())[0]["language"]

    @property
    def forms(self) -> List[Form]:
        """
        List of all forms

        :rtype: List[Form]
        """
        return [Form(f) for f in super().get("forms", [])]

    @property
    def senses(self) -> List[Sense]:
        """
        List of all senses

        :rtype: List[Sense]
        """
        return [Sense(s) for s in super().get("senses", [])]

    def createSense(self, glosses: Dict[str, str], claims=None) -> str:
        """Create a sense for the lexeme

        :param glosses: glosses for the sense
        :type  glosses: Dict[str, str]
        :param claims: claims to add to the new form (Default value = None) -> st)
        :rtype: str

        """
        # Create the json with the sense's data
        data_sense: Dict[str, Dict[str, Dict[str, str]]] = {"glosses": {}}
        for lang, gloss in glosses.items():
            data_sense["glosses"][lang] = {"value": gloss, "language": lang}

        # send a post to add sense to lexeme
        PARAMS = {
            "action": "wbladdsense",
            "format": "json",
            "lexemeId": self["id"],
            "token": "__AUTO__",
            "bot": "1",
            "data": json.dumps(data_sense),
        }
        DATA = self.repo.post(PARAMS)
        addedSense = Sense(DATA["sense"])
        idSense = DATA["sense"]["id"]
        logging.info("---Created sense: idsense = %s", idSense)

        # Add the claims
        if claims:
            addedSense.__setClaims__(self.repo, claims)

        # Add the created form to the local lexeme
        self["senses"].append(addedSense)

        return idSense

    def createForm(
        self, form: str, infosGram: List[str], language: Language = None, claims=None
    ) -> str:
        """Create a form for the lexeme

        :param form: the new form to add
        :type  form: str
        :param infosGram: grammatical features
        :type  infosGram: List[str]
        :param language: the language of the form
        :type  language: Optional[Language]
        :param claims: claims to add to the new form (Default value = None) -> st)
        :returns: The id of the form
        :rtype: str

        """

        if language is None:
            languagename = self.language
        else:
            languagename = language.short

        # Create the json with the forms's data
        data_form = json.dumps(
            {
                "representations": {
                    languagename: {"value": form, "language": languagename}
                },
                "grammaticalFeatures": infosGram,
            }
        )

        # send a post to add form to lexeme
        PARAMS = {
            "action": "wbladdform",
            "format": "json",
            "lexemeId": self["id"],
            "token": "__AUTO__",
            "bot": "1",
            "data": data_form,
        }
        DATA = self.repo.post(PARAMS)
        addedForm = Form(DATA["form"])
        idForm = DATA["form"]["id"]
        logging.info("---Created form: idForm = %s", idForm)

        # Add the claims
        if claims:
            addedForm.__setClaims__(self.repo, claims)

        # Add the created form to the local lexeme
        self["forms"].append(addedForm)

        return idForm

    def createClaims(self, claims):
        """Add claims to the Lexeme

        :param claims: The set of claims to be added

        """
        self.__setClaims__(self.repo, claims)

    def __repr__(self) -> str:
        return "<Lexeme '{}'>".format(self["id"])