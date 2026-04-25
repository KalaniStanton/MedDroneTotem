import pygame
import math
import random
import time

# --- CONFIGURATION ---
W, H = 400, 400
FPS = 60
C_BG_TOP = (223, 244, 240)
C_BG_BTM = (194, 232, 226)
C_SHAPE = (23, 37, 46)

EXPRESSION_INTERVAL = 5.0  # Seconds between automatic expression changes


# --- MATH HELPERS ---
def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def ease(t):
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t


# --- EXPRESSIONS ---
# Format: { 'eyeL': [cx, cy, rw, rh, angle, r], 'mouth': [cx, cy, bw, bh, gap, liftL, liftR, tilt] }
FACES = {
    "normal": {
        "eyeL": [0.27, 0.30, 0.12, 0.08, 0, 10],
        "eyeR": [0.73, 0.30, 0.12, 0.08, 0, 10],
        "mouth": [0.50, 0.64, 0.13, 0.11, 0.22, 0, 0, 0],
    },
    "happy": {
        "eyeL": [0.27, 0.29, 0.13, 0.10, 0, 15],
        "eyeR": [0.73, 0.29, 0.13, 0.10, 0, 15],
        "mouth": [0.50, 0.65, 0.15, 0.14, 0.20, -0.15, -0.15, 0],
    },
    "blink": {
        "eyeL": [0.27, 0.30, 0.12, 0.01, 0, 2],
        "eyeR": [0.73, 0.30, 0.12, 0.01, 0, 2],
        "mouth": [0.50, 0.64, 0.13, 0.11, 0.22, 0, 0, 0],
    },
    "wonder": {
        "eyeL": [0.27, 0.26, 0.16, 0.16, 0, 60],  # Larger, perfectly circular
        "eyeR": [0.73, 0.26, 0.16, 0.16, 0, 60],
        "mouth": [0.50, 0.70, 0.12, 0.18, 0.08, 0, 0, 0],  # Tall, wide "O"
    },
    "bobbing": {
        "eyeL": [0.27, 0.30, 0.12, 0.005, 0, 2],  # Eyes closed (same as blink)
        "eyeR": [0.73, 0.30, 0.12, 0.005, 0, 2],
        "mouth": [0.50, 0.65, 0.14, 0.11, 0.22, -0.1, -0.1, 0],  # Gentle smile
    },
    "sad": {
        "eyeL": [0.275, 0.32, 0.10, 0.07, 0.1, 8],  # Eyes slightly narrower and tilted
        "eyeR": [0.725, 0.32, 0.10, 0.07, -0.1, 8],
        "mouth": [
            0.50,
            0.62,
            0.12,
            0.10,
            0.18,
            0.12,
            0.12,
            0,
        ],  # Lift is positive (down)
    },
    "smirk": {
        "eyeL": [0.26, 0.30, 0.13, 0.08, -0.2, 10],  # Tilted inward
        "eyeR": [0.74, 0.28, 0.13, 0.09, 0.1, 10],  # Slightly higher and tilted out
        "mouth": [0.52, 0.64, 0.13, 0.11, 0.24, -0.08, 0.04, 0.08],
        # cx slightly right, liftL is UP, liftR is DOWN, tilt is positive
    },
}


class MedBot:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()

        self.cur_face = FACES["normal"]
        self.target_face = FACES["normal"]
        self.anim_t = 1.0

        # Surface for the "Liquid" Mouth effect
        self.mouth_surf = pygame.Surface((W, H), pygame.SRCALPHA)

        self.sequence = ["normal", "smirk", "wonder", "bobbing", "happy", "sad"]
        self.seq_idx = 0

        self.next_event = time.time() + EXPRESSION_INTERVAL

        # Blink Logic
        self.next_blink = time.time() + random.uniform(2.0, 6.0)
        self.is_blinking = False
        self.pre_blink_face = "normal"
        self.cur_eye = FACES["normal"]["eyeL"]  # We'll just track one side for the lerp
        self.target_eye = FACES["normal"]["eyeL"]

        self.cur_mouth = FACES["normal"]["mouth"]
        self.target_mouth = FACES["normal"]["mouth"]

        self.anim_t = 1.0
        self.eye_t = 1.0  # Separate timer for eyes

    def lerp_part(self, a, b, t):
        return [lerp(av, bv, t) for av, bv in zip(a, b)]

    def draw_rounded_rect(self, surf, color, rect, radius):
        pygame.draw.rect(surf, color, rect, border_radius=int(radius))

    def draw_mouth_liquid(self, m, offset_y=0, tilt_extra=0):
        self.mouth_surf.fill((0, 0, 0, 0))

        cx, cy = m[0] * W, (m[1] * H) + offset_y
        bw, bh = m[2] * W, m[3] * H
        hg = (m[4] * W) / 2
        lL, lR = m[5] * H / 2, m[6] * H / 2
        rh = bh / 2

        # Combine base mouth tilt (m[7]) with animation tilt (tilt_extra)
        total_tilt = m[7] + tilt_extra

        # 1. Create a surface for the raw shapes
        temp_surf = pygame.Surface((W, H), pygame.SRCALPHA)

        # 2. Draw the parts relative to the center
        # Left Pillar
        self.draw_rounded_rect(
            temp_surf, C_SHAPE, (cx - hg - bw, cy + lL - rh, bw, bh), 12
        )
        # Right Pillar
        self.draw_rounded_rect(temp_surf, C_SHAPE, (cx + hg, cy + lR - rh, bw, bh), 12)
        # Center Ribbon
        pygame.draw.rect(temp_surf, C_SHAPE, (cx - hg - 2, cy - rh, (hg * 2) + 4, bh))

        # 3. Apply the Liquid Blur
        blurred = pygame.transform.gaussian_blur(temp_surf, 6)
        liquid_mouth = pygame.mask.from_surface(blurred, threshold=140).to_surface(
            setcolor=C_SHAPE, unsetcolor=(0, 0, 0, 0)
        )

        # 4. ROTATION: Rotate the final liquid shape around the mouth center
        if total_tilt != 0:
            # Rotate the surface
            rotated_surf = pygame.transform.rotate(
                liquid_mouth, math.degrees(-total_tilt)
            )
            # Recenter the rotated surface
            new_rect = rotated_surf.get_rect(center=(W // 2, H // 2))
            self.screen.blit(rotated_surf, new_rect.topleft)
        else:
            self.screen.blit(liquid_mouth, (0, 0))

    def update(self):
        if self.anim_t < 1.0:
            self.anim_t += 0.05  # Morph speed

        t = ease(clamp(self.anim_t, 0, 1))

        # Interpolate eye and mouth states
        eyeL = self.lerp_part(self.cur_face["eyeL"], self.target_face["eyeL"], t)
        eyeR = self.lerp_part(self.cur_face["eyeR"], self.target_face["eyeR"], t)
        mouth = self.lerp_part(self.cur_face["mouth"], self.target_face["mouth"], t)

        # Draw Background
        self.screen.fill(C_BG_TOP)  # Simplified gradient

        # Draw Eyes
        for e in [eyeL, eyeR]:
            ex, ey = e[0] * W, e[1] * H
            ew, eh = e[2] * W, e[3] * H
            self.draw_rounded_rect(
                self.screen, C_SHAPE, (ex - ew, ey - eh, ew * 2, eh * 2), e[5]
            )

        # Draw Mouth
        self.draw_mouth_liquid(mouth)

        # CRT Scanlines
        for y in range(0, H, 4):
            pygame.draw.line(self.screen, (0, 0, 0, 20), (0, y), (W, y))

    def set_mouth(self, key):
        if key in FACES:
            self.cur_mouth = self.lerp_part(
                self.cur_mouth, self.target_mouth, ease(clamp(self.anim_t, 0, 1))
            )
            self.target_mouth = FACES[key]["mouth"]
            self.anim_t = 0.0

    def set_eyes(self, key, speed=0.05):
        if key in FACES:
            # eyeL and eyeR usually share the same "state" (open/closed)
            self.cur_eye = self.lerp_part(
                self.cur_eye, self.target_eye, ease(clamp(self.eye_t, 0, 1))
            )
            self.target_eye = FACES[key]["eyeL"]
            self.eye_t = 0.0
            self.eye_speed = speed  # Blinks are usually faster than morphs

    def update_and_draw(self):
        self.anim_t += 0.05
        self.eye_t += getattr(self, "eye_speed", 0.05)

        mt = ease(clamp(self.anim_t, 0, 1))
        et = ease(clamp(self.eye_t, 0, 1))

        eye_now = self.lerp_part(self.cur_eye, self.target_eye, et)
        mouth_now = self.lerp_part(self.cur_mouth, self.target_mouth, mt)

        # --- ANIMATION OVERLAYS ---
        bob_y = 0
        bob_tilt = 0
        scan_x = 0

        current_mood = self.sequence[self.seq_idx]

        if current_mood == "bobbing":
            bob_y = math.sin(time.time() * 8) * 15
            bob_tilt = math.sin(time.time() * 4) * 0.15

        if current_mood == "wonder":
            # Slower, sweeping motion (speed 3 instead of 12)
            # We use math.pow to make the transition through the center faster
            # and the pause at the ends longer (the "linger")
            raw_sine = math.sin(time.time() * 3)

            # This "shapes" the sine wave to linger at the far left/right
            scan_x = math.copysign(math.pow(abs(raw_sine), 0.7), raw_sine) * 25

            # Add a very slight vertical "float" to the eyes for a dreamy feel
            bob_y = math.sin(time.time() * 1.5) * 8

        self.screen.fill(C_BG_TOP)

        # Draw Eyes
        for side in [-1, 1]:
            # Apply scan_x to the eye position
            cx = (0.5 + (0.23 * side)) * W + scan_x
            ey = (eye_now[1] * H) + bob_y
            ew, eh = eye_now[2] * W, eye_now[3] * H
            angle = (eye_now[4] + bob_tilt) * side

            self.draw_rounded_rect(
                self.screen, C_SHAPE, (cx - ew, ey - eh, ew * 2, eh * 2), eye_now[5]
            )

        # Draw Mouth
        self.draw_mouth_liquid(mouth_now, offset_y=bob_y, tilt_extra=bob_tilt)

    def run(self):
        running = True
        while running:
            now = time.time()

            # --- 1. AUTO MOUTH CYCLE ---
            if now > self.next_event:
                self.seq_idx = (self.seq_idx + 1) % len(self.sequence)
                new_key = self.sequence[self.seq_idx]
                self.set_mouth(new_key)
                # Also set the "resting" eye state for that expression
                if not self.is_blinking:
                    self.set_eyes(new_key, speed=0.05)
                self.next_event = now + EXPRESSION_INTERVAL

            # --- 2. INDEPENDENT BLINK ---
            if not self.is_blinking and now > self.next_blink:
                self.is_blinking = True
                self.set_eyes("blink", speed=0.2)  # Fast close
                self.blink_timeout = now + 0.12

            if self.is_blinking and now > self.blink_timeout:
                self.is_blinking = False
                # Return eyes to whatever the current expression is
                current_expr = self.sequence[self.seq_idx]
                self.set_eyes(current_expr, speed=0.2)  # Fast open
                self.next_blink = now + random.uniform(2.0, 8.0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        self.set_mouth("normal")
                        self.set_eyes("normal")
                    if event.key == pygame.K_2:
                        self.set_mouth("happy")
                        self.set_eyes("happy")
                    if event.key == pygame.K_3:
                        self.set_mouth("sad")
                        self.set_mouth("sad")
                    if event.key == pygame.K_b:
                        self.set_eyes("blink")
            self.update_and_draw()  # Call your drawing logic
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    MedBot().run()
