unhealthy_foods = ["donuts", "cake", "candies", "bloomin' onion", "twinkies", "giant red cake"]
healthly_foods = ["vegetables", "fruits", "eggs", "chicken breast"]

answer = input("what is your favorite food?\n")

if answer in unhealthy_foods:
    person_is_healthy = False

elif answer in healthly_foods:
    person_is_healthy = True

else:
    person_is_healthy = None # ??

if (person_is_healthy == True):
    print("Good job, keep it up! ✅✅✅")

elif (person_is_healthy == False):
    print("You need to make better choices! ❌❌❌")

else:
    print("??? idk")

print("fin.")