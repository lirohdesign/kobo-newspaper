from datetime import datetime

QUESTIONS = [
    ("have a pet dinosaur", "have a pet dragon"),
    ("be as small as an ant", "be as tall as a giraffe"),
    ("talk to land animals", "talk to sea animals"),
    ("live in a giant treehouse", "live in a secret cave"),
    ("ride on the back of an ostrich", "ride on the back of a dolphin"),
    ("have a slide for your bedroom stairs", "have a trampoline for your floor"),
    ("slide down a rainbow", "jump on a fluffy cloud"),
    ("sneeze harmless popcorn", "laugh out jellybeans"),
    ("only wear pajamas for a whole month", "only wear a fancy costume for a whole month"),
    ("fly like a bird", "swim like a dolphin"),
    ("have a robot that cleans your room", "have a robot that makes your snacks"),
    ("be super fast", "be super strong"),
    ("find a hidden treasure map", "discover a secret passage in your house"),
    ("eat only pizza forever", "eat only tacos forever"),
    ("have a magic wand", "have a flying carpet"),
    ("be a pirate", "be an astronaut"),
    ("live underwater", "live on the moon"),
    ("have a pet elephant", "have a pet whale"),
    ("be able to speak every language", "be able to play every instrument"),
    ("never have to sleep", "never have to eat vegetables"),
    ("have x-ray vision", "have super hearing"),
    ("go back in time", "travel to the future"),
    ("have a personal chef", "have a personal robot helper"),
    ("explore a jungle", "explore a desert island"),
    ("be a famous inventor", "be a famous explorer"),
    ("eat ice cream for breakfast every day", "eat cake for dinner every day"),
    ("be invisible for a day", "be able to fly for a day"),
    ("meet a friendly alien", "discover a new animal species"),
    ("have a magical backpack that always has what you need", "have magical shoes that take you anywhere"),
    ("swim with dolphins", "fly with eagles"),
    ("live in a castle", "live in a spaceship"),
    ("have a tree that grows candy", "have a pond full of lemonade"),
    ("always know the answer in class", "always be picked first for teams"),
    ("have a dog that can talk", "have a cat that can grant wishes"),
    ("be a chef at a fancy restaurant", "be a zookeeper at a cool zoo"),
    ("spend a week on a pirate ship", "spend a week in a submarine"),
    ("have an extra hour every day", "have an extra day every week"),
    ("never get tired", "never get bored"),
    ("be able to breathe underwater", "be able to survive in outer space"),
    ("fight one horse-sized duck", "fight ten duck-sized horses"),
    ("have a giant pillow fort that never falls down", "have a blanket that keeps you exactly the right temperature"),
    ("be best friends with a dragon", "be best friends with a unicorn"),
    ("know how to do every sport", "know how to play every instrument"),
    ("have your own island", "have your own mountain"),
    ("always have the best snacks", "always have the best toys"),
    ("be able to pause time", "be able to rewind time"),
    ("have a hot air balloon", "have a submarine"),
    ("discover a new planet", "discover treasure at the bottom of the sea"),
    ("live in a world made of candy", "live in a world made of toys"),
    ("have free ice cream for life", "have free pizza for life"),
]


def collect_wyr(today=None):
    if today is None:
        today = datetime.now()
    idx = today.timetuple().tm_yday % len(QUESTIONS)
    option_a, option_b = QUESTIONS[idx]
    return (
        f"<div class='wyr-block'>"
        f"<p class='wyr-option'>{option_a}</p>"
        f"<p class='wyr-or'>— or —</p>"
        f"<p class='wyr-option'>{option_b}</p>"
        f"</div>"
    )
