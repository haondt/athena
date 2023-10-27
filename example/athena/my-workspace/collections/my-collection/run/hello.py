from athena.client import Athena

def run(athena: Athena):
    cheese = athena.get_variable("cheese")
    print("cheese:", cheese)


