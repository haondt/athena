from ._metadata import __version__
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
