import os


WIDTH = 12
HEIGHT = 9
LEVEL_COUNT = 5
START = [0, 0]
EXIT = [WIDTH - 1, HEIGHT - 1]


def random_index(limit):
    return int.from_bytes(os.urandom(4), "big") % limit


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


class StarRunner:
    def __init__(self):
        self.level = 1
        self.score = 0
        self.health = 3
        self.max_health = 5
        self.shield = False
        self.energy = 0
        self.frozen_turns = 0
        self.running = True
        self.won = False
        self.message = "Собери все звёзды и найди выход."
        self.start_level()

    def start_level(self):
        self.player = START.copy()
        self.star_goal = 3 + self.level
        self.stars = []
        self.items = {}
        self.enemies = []

        for _ in range(self.star_goal):
            self.stars.append(self.random_empty_cell())

        for _ in range(min(1 + self.level, 4)):
            self.enemies.append({"pos": self.random_empty_cell(), "hp": 1, "boss": False})

        if self.level in (3, 5):
            boss_hp = 2 if self.level == 3 else 4
            self.enemies.append({"pos": self.random_empty_cell(), "hp": boss_hp, "boss": True})

        item_types = ["+", "S", "~"]
        for item in item_types:
            self.items[tuple(self.random_empty_cell())] = item

    def random_empty_cell(self):
        occupied = {tuple(self.player), tuple(EXIT)}
        occupied.update(tuple(star) for star in self.stars)
        occupied.update(self.items)
        occupied.update(tuple(enemy["pos"]) for enemy in self.enemies)
        available = [
            [x, y]
            for y in range(HEIGHT)
            for x in range(WIDTH)
            if (x, y) not in occupied
        ]
        if not available:
            raise RuntimeError("На поле не осталось свободных клеток.")
        return available[random_index(len(available))]

    def boss_alive(self):
        return any(enemy["boss"] for enemy in self.enemies)

    def portal_open(self):
        return not self.stars and not self.boss_alive()

    def draw(self):
        board = [["." for _ in range(WIDTH)] for _ in range(HEIGHT)]
        board[EXIT[1]][EXIT[0]] = ">" if self.portal_open() else "#"

        for star in self.stars:
            board[star[1]][star[0]] = "*"
        for (x, y), item in self.items.items():
            board[y][x] = item
        for enemy in self.enemies:
            x, y = enemy["pos"]
            board[y][x] = "B" if enemy["boss"] else "X"
        board[self.player[1]][self.player[0]] = "P"

        clear_screen()
        print("=== STARBOUND ESCAPE ===")
        print(f"Уровень: {self.level}/{LEVEL_COUNT}   Очки: {self.score}")
        print(f"Здоровье: {self.health}/{self.max_health} HP")
        print(f"Заряды: {self.energy}   Щит: {'да' if self.shield else 'нет'}"
              f"   Заморозка: {self.frozen_turns}")
        print(f"Осталось звёзд: {len(self.stars)}")
        print()
        for row in board:
            print(" ".join(row))
        print()
        print("P ты  * звезда  X враг  B босс  + аптечка  S щит  ~ заморозка")
        print("# закрытый портал  > открытый портал")
        print("WASD — движение | F — атака рядом | Q — выход")
        print(self.message)

    def collect_at_player(self):
        for index, star in enumerate(self.stars):
            if star == self.player:
                del self.stars[index]
                self.score += 10
                self.energy += 1
                self.message = "Звезда собрана: +10 очков и один заряд атаки."
                break

        item = self.items.pop(tuple(self.player), None)
        if item == "+":
            old_health = self.health
            self.health = min(self.max_health, self.health + 1)
            self.message = (
                "Аптечка! Здоровье восстановлено."
                if self.health > old_health
                else "Аптечка найдена, но здоровье уже полное."
            )
        elif item == "S":
            self.shield = True
            self.message = "Щит активирован: он защитит от одного удара."
        elif item == "~":
            self.frozen_turns = 3
            self.message = "Заморозка! Враги пропустят три своих хода."

    def take_hit(self, message):
        if self.shield:
            self.shield = False
            self.message = f"Щит поглотил удар! {message}"
        else:
            self.health -= 1
            self.message = f"Получен удар! {message}"

        self.player = START.copy()
        if self.health <= 0:
            self.running = False

    def move_player(self, command):
        directions = {
            "w": (0, -1),
            "a": (-1, 0),
            "s": (0, 1),
            "d": (1, 0),
        }
        dx, dy = directions[command]
        previous_position = self.player.copy()
        new_position = [self.player[0] + dx, self.player[1] + dy]
        if not (0 <= new_position[0] < WIDTH and 0 <= new_position[1] < HEIGHT):
            self.message = "Край поля! Попробуй пойти в другую сторону."
            return False

        self.player = new_position
        for enemy in self.enemies:
            if enemy["pos"] == self.player:
                self.take_hit("Ты столкнулся с врагом.")
                if not enemy["boss"]:
                    enemy["pos"] = self.random_empty_cell()
                return True

        self.collect_at_player()
        if self.player == EXIT:
            self.finish_level(previous_position)
            return True
        return True

    def attack(self):
        if self.energy == 0:
            self.message = "Нет зарядов! Собирай звёзды, чтобы атаковать."
            return False

        targets = [
            enemy
            for enemy in self.enemies
            if abs(enemy["pos"][0] - self.player[0])
            + abs(enemy["pos"][1] - self.player[1]) <= 2
        ]
        if not targets:
            self.message = "Рядом нет цели. Подойди к врагу на две клетки."
            return False

        target = min(
            targets,
            key=lambda enemy: abs(enemy["pos"][0] - self.player[0])
            + abs(enemy["pos"][1] - self.player[1]),
        )
        self.energy -= 1
        target["hp"] -= 1
        if target["hp"] == 0:
            self.enemies.remove(target)
            self.score += 25 if target["boss"] else 5
            self.message = "Босс побеждён! +25 очков." if target["boss"] else "Враг побеждён! +5 очков."
        else:
            self.message = f"Попадание! У босса осталось {target['hp']} здоровья."
        return True

    def move_enemies(self):
        if self.frozen_turns:
            self.frozen_turns -= 1
            self.message += f" Враги заморожены ещё на {self.frozen_turns} ход."
            return

        for enemy in self.enemies:
            x, y = enemy["pos"]
            dx = 0
            dy = 0
            if x != self.player[0] and (y == self.player[1] or random_index(2) == 0):
                dx = 1 if x < self.player[0] else -1
            elif y != self.player[1]:
                dy = 1 if y < self.player[1] else -1

            new_x, new_y = x + dx, y + dy
            if not (0 <= new_x < WIDTH and 0 <= new_y < HEIGHT):
                continue
            if [new_x, new_y] == EXIT:
                continue
            if any(other is not enemy and other["pos"] == [new_x, new_y]
                   for other in self.enemies):
                continue
            enemy["pos"] = [new_x, new_y]

            if enemy["pos"] == self.player:
                self.take_hit("Враг настиг тебя.")
                return

    def finish_level(self, previous_position):
        if not self.portal_open():
            self.player = previous_position
            self.message = "Портал заперт! Собери все звёзды и победи босса."
            return

        if self.level == LEVEL_COUNT:
            self.won = True
            self.running = False
            return

        self.level += 1
        self.health = min(self.max_health, self.health + 1)
        self.start_level()
        self.message = (
            f"Уровень пройден! Ты восстановил здоровье. "
            f"Впереди уровень {self.level}."
        )

    def play(self):
        print("Пилот, космические пираты украли звёздные ядра.")
        print("Собери звёзды на пяти планетах, одолей боссов")
        print("и открой портал домой. По пути ищи полезные бонусы!")
        input("\nНажми Enter, чтобы начать...")

        while self.running:
            self.draw()
            command = input("\nТвой ход: ").strip().lower()
            if command == "q":
                print("Полет завершён. Удачи в следующий раз!")
                return
            if command in ("w", "a", "s", "d"):
                spent_turn = self.move_player(command)
            elif command == "f":
                spent_turn = self.attack()
            else:
                self.message = "Используй W, A, S, D для движения, F для атаки или Q для выхода."
                continue

            if spent_turn and self.running:
                self.move_enemies()

        self.draw()
        if self.won:
            print("\nТы победил пиратов и вернулся домой! Поздравляем!")
            print(f"Финальный счёт: {self.score}")
        else:
            print("\nКорабль потерян. Попробуй ещё раз!")
            print(f"Счёт: {self.score}")
        input("Нажми Enter, чтобы выйти...")


if __name__ == "__main__":
    StarRunner().play()
