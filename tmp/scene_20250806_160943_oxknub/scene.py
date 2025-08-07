from manim import *

class MainScene(Scene):
    def construct(self):
        # Colors
        red = "#FF6B6B"
        cyan = "#4ECDC4"
        blue = "#45B7D1"
        yellow = "#FFD93D"

        # 1. Title Introduction (8s)
        title_text = Text("Solving Quadratic Equations", color=blue).scale(1.2)
        self.play(Write(title_text))
        self.wait(2)
        self.play(title_text.animate.to_edge(UP))

        subtitle_text = Text("Focusing on x² = 0", color=yellow).scale(0.8)
        self.play(Write(subtitle_text))
        self.wait(3)
        self.play(FadeOut(title_text), FadeOut(subtitle_text))
        self.wait(3)

        # 2. Problem Setup (10s)
        problem_title = Text("Our Problem:", color=blue).scale(1)
        problem_equation = MathTex("x^2 = 0", color=red).scale(2)

        self.play(Write(problem_title.to_edge(UP)))
        self.wait(1)
        self.play(Write(problem_equation))
        self.wait(4)

        explanation_text = Text("We want to find the value(s) of 'x'", color=cyan).scale(0.7)
        explanation_text.next_to(problem_equation, DOWN, buff=0.5)
        self.play(Write(explanation_text))
        self.wait(5)
        self.play(FadeOut(problem_title), FadeOut(problem_equation), FadeOut(explanation_text))
        self.wait(2)

        # 3. Step-by-step solution (25s)
        solution_title = Text("Step-by-Step Solution", color=blue).scale(1)
        self.play(Write(solution_title.to_edge(UP)))
        self.wait(2)

        # Step 1: The Equation
        step1_title = Text("Step 1: The Equation", color=yellow).scale(0.7).to_edge(LEFT).shift(UP*1.5)
        step1_equation = MathTex("x^2 = 0", color=red).scale(1.5).next_to(step1_title, DOWN, buff=0.5)
        self.play(Write(step1_title))
        self.play(Write(step1_equation))
        self.wait(3)

        # Step 2: Taking the Square Root
        step2_title = Text("Step 2: Take the Square Root", color=yellow).scale(0.7).next_to(step1_title, RIGHT, buff=1.5)
        step2_explanation = Text("To isolate 'x', we take the square root of both sides.", color=cyan).scale(0.5).next_to(step2_title, DOWN, buff=0.5)
        step2_equation_left = MathTex("\\\sqrt{x^2}", color=red).scale(1.5)
        step2_equation_right = MathTex("= \\\sqrt{0}", color=red).scale(1.5)
        step2_equation_combined = VGroup(step2_equation_left, step2_equation_right).arrange(RIGHT, buff=0.2)

        self.play(Write(step2_title))
        self.play(Write(step2_explanation))
        self.wait(3)
        self.play(Transform(step1_equation, step2_equation_combined))
        self.wait(4)

        # Step 3: Simplifying
        step3_title = Text("Step 3: Simplify", color=yellow).scale(0.7).next_to(step1_title, DOWN, buff=2)
        step3_explanation = Text("The square root of x² is x. The square root of 0 is 0.", color=cyan).scale(0.5).next_to(step3_title, DOWN, buff=0.5)
        step3_equation_left = MathTex("x", color=red).scale(1.5)
        step3_equation_right = MathTex("= 0", color=red).scale(1.5)
        step3_equation_combined = VGroup(step3_equation_left, step3_equation_right).arrange(RIGHT, buff=0.2)

        self.play(Write(step3_title))
        self.play(Write(step3_explanation))
        self.wait(3)
        self.play(Transform(step1_equation, step3_equation_combined))
        self.wait(4)
        self.play(FadeOut(step1_title), FadeOut(step2_title), FadeOut(step3_title), FadeOut(step2_explanation), FadeOut(step3_explanation))
        self.wait(2)

        # 4. Visual Demonstration (12s)
        visual_title = Text("Visualizing the Solution", color=blue).scale(1)
        self.play(Write(visual_title.to_edge(UP)))
        self.wait(2)

        # Graph of y = x^2
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 4, 1],
            x_length=5,
            y_length=4,
            axis_config={"include_numbers": True, "color": WHITE}
        )
        labels = axes.get_axis_labels(x_label="x", y_label="y")

        parabola = axes.plot(lambda x: x**2, color=red)
        parabola_label = MathTex("y = x^2", color=red).scale(0.7).next_to(parabola, UP, buff=0.2)

        self.play(Create(axes), Write(labels))
        self.play(Create(parabola), Write(parabola_label))
        self.wait(3)

        # The line y = 0
        zero_line = axes.get_horizontal_line(0, color=yellow)
        zero_line_label = Text("y = 0", color=yellow).scale(0.7).next_to(zero_line, RIGHT, buff=0.2)

        self.play(Create(zero_line), Write(zero_line_label))
        self.wait(3)

        # Intersection point
        intersection_point = Dot(point=axes.c2p(0, 0), color=cyan)
        intersection_label = Text("x = 0", color=cyan).scale(0.7).next_to(intersection_point, DOWN, buff=0.2)

        self.play(FadeIn(intersection_point), Write(intersection_label))
        self.wait(3)
        self.play(FadeOut(axes), FadeOut(labels), FadeOut(parabola), FadeOut(parabola_label), FadeOut(zero_line), FadeOut(zero_line_label), FadeOut(intersection_point), FadeOut(intersection_label))
        self.wait(1)
        self.play(FadeOut(visual_title))
        self.wait(1)

        # 5. Summary (5s)
        summary_title = Text("Summary", color=blue).scale(1)
        summary_equation = MathTex("x^2 = 0", color=red).scale(1.5)
        summary_solution = MathTex("\\implies x = 0", color=cyan).scale(1.5)
        summary_vgroup = VGroup(summary_equation, summary_solution).arrange(RIGHT, buff=0.5)

        self.play(Write(summary_title.to_edge(UP)))
        self.wait(1)
        self.play(Write(summary_vgroup))
        self.wait(3)
        self.play(FadeOut(summary_title), FadeOut(summary_vgroup))
        self.wait(1)