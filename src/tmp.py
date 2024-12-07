import random

rps: list[str] = ["Rock", "Paper", "Scissors"]

my_pick = ""

while my_pick not in rps:
    my_pick: str = input("My Pick: ").title()

my_index = rps.index(my_pick)
opponent_index = random.randint(0, len(rps) - 1)

diff: int = my_index - opponent_index

if diff == -1:
    print("Opponent Wins")
elif diff == 1:
    print("You Win")
else:
    print("Tie")