import logging
import time
from typing import Any, Dict, Optional

import requests

from .version import user_agent


class WikidataSession:
    """
    Wikidata network and authentication session.
    Needed for everything this framework does.
    """

    URL: str = "https://www.wikidata.org/w/api.php"
    assertUser: Optional[str] = None
    maxlag: int = 5

    def __init__(
            self,
            username: Optional[str] = None,
            password: Optional[str] = None,
            token: Optional[str] = None,
            auth: Optional[str] = None,
            user_agent: str = user_agent,
    ):
        """
        Create a wikidata session by login in and getting the token
        """
        self.username = username
        self.password = password
        self.auth = auth
        self.headers = {"User-Agent": user_agent}
        self.S = requests.Session()
        if username is not None and password is not None:
            # Since logins don't put load on the servers
            # we set maxlag higher for these requests.
            self.maxlag = 30
            self.login()
            self.maxlag = 5
        if token is not None:
            self.CSRF_TOKEN = token
        # After login enable 'assertUser'-feature of the Mediawiki-API to
        # make sure to never edit accidentally as IP
        if username is not None:
            # truncate bot name if a "bot password" is used
            self.assertUser = username.split("@")[0]

    def login(self):
        # Ask for a token
        PARAMS_1 = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        }
        data = self.get(PARAMS_1)
        LOGIN_TOKEN = data["query"]["tokens"]["logintoken"]

        # connexion request
        PARAMS_2 = {
            "action": "login",
            "lgname": self.username,
            "lgpassword": self.password,
            "format": "json",
            "lgtoken": LOGIN_TOKEN,
        }
        data = self.post(PARAMS_2)
        if data.get("login", []).get("result") != "Success":
            raise PermissionError("Login failed", data["login"]["reason"])
        logging.info("Log in succeeded")

        PARAMS_3 = {
            "action": "query",
            "meta": "tokens",
            "format": "json"
        }
        data = self.get(PARAMS_3)
        self.CSRF_TOKEN = data["query"]["tokens"]["csrftoken"]
        logging.info("Got CSRF token: %s", self.CSRF_TOKEN)

    def post(self, data: Dict[str, str]) -> Any:
        """Send data to wikidata by POST request. The CSRF token is automatically
        filled in if __AUTO__ is given instead.

        :param data: Parameters to send via POST
        :type  data: Dict[str, str])
        :returns: Answer form the server as Objekt
        :rtype: Any

        """
        if data.get("token") == "__AUTO__":
            data["token"] = self.CSRF_TOKEN
        if "assertuser" not in data and self.assertUser is not None:
            data["assertuser"] = self.assertUser
        data["maxlag"] = str(self.maxlag)
        R = self.S.post(self.URL, data=data, headers=self.headers, auth=self.auth)
        if R.status_code != 200:
            raise Exception(
                "POST was unsuccessfull ({}): {}".format(R.status_code, R.text)
            )
        DATA = R.json()
        if "error" in DATA:
            if DATA["error"]["code"] == "maxlag":
                sleepfor = float(R.headers.get("retry-after", 5))
                logging.info("Maxlag hit, waiting for %.1f seconds", sleepfor)
                time.sleep(sleepfor)
                return self.post(data)
            else:
                raise PermissionError("API returned error: " + str(DATA["error"]))
        logging.debug("Post request succeed")
        return DATA

    def get(self, data: Dict[str, str]) -> Any:
        """Send a GET request to wikidata

        :param data: Parameters to send via GET
        :type  data: Dict[str, str]
        :returns: Answer form the server as Objekt
        :rtype: Any

        """
        R = self.S.get(self.URL, params=data, headers=self.headers)
        DATA = R.json()
        if R.status_code != 200 or "error" in DATA:
            # We do not set maxlag for GET requests – so this error can only
            # occur if the users sets maxlag in the request data object
            if DATA["error"]["code"] == "maxlag":
                sleepfor = float(R.headers.get("retry-after", 5))
                logging.info("Maxlag hit, waiting for %.1f seconds", sleepfor)
                time.sleep(sleepfor)
                return self.get(data)
            else:
                raise Exception(
                    "GET was unsuccessfull ({}): {}".format(R.status_code, R.text)
                )
        logging.debug("Get request succeed")
        return DATA
