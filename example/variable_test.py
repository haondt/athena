from athena.client import Athena

def run(athena: Athena):
    x = athena.variable.str['base_url']
    print(x)
