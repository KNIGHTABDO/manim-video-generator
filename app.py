from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from flask_cors import CORS
import os
import tempfile
import subprocess
import logging
import uuid
import shutil
import json
from manim import *
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime
import time
import random
import io
from telegram_bot import (
    notify_generation_start, 
    notify_generation_success, 
    notify_generation_error,
    notify_system_alert,
    telegram_notifier
)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static')

# Enable CORS for all routes
CORS(app)

# Add ngrok-specific headers
@app.after_request
def after_request(response):
    # Add headers for ngrok compatibility
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, ngrok-skip-browser-warning'
    return response

app.logger.setLevel(logging.INFO)

# Configure Manim
config.media_dir = "media"
config.video_dir = "videos"
config.images_dir = "images"
config.text_dir = "texts"
config.tex_dir = "tex"
config.log_dir = "log"
config.renderer = "cairo"
config.text_renderer = "cairo"
config.use_opengl_renderer = False

# Set up required directories
def setup_directories():
    """Create all required directories for the application"""
    directories = [
        os.path.join(app.root_path, 'static'),
        os.path.join(app.root_path, 'static', 'videos'),
        os.path.join(app.root_path, 'tmp'),
        os.path.join(app.root_path, 'media'),
        os.path.join(app.root_path, 'media', 'videos'),
        os.path.join(app.root_path, 'media', 'videos', 'scene'),
        os.path.join(app.root_path, 'media', 'videos', 'scene', '720p30'),
        os.path.join(app.root_path, 'media', 'videos', 'scene', '1080p60')
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        app.logger.info(f'Created directory: {directory}')

# Set up directories at startup
setup_directories()

# Ensure static directory exists
os.makedirs(os.path.join(app.root_path, 'static', 'videos'), exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Google GenAI client
genai_client = genai.Client(api_key='AIzaSyAX1h0FQy88LagtmdrcVuxT6v9Lz8oyers')

# Set media and temporary directories with fallback to local paths
if os.environ.get('DOCKER_ENV'):
    app.config['MEDIA_DIR'] = os.getenv('MEDIA_DIR', '/app/media')
    app.config['TEMP_DIR'] = os.getenv('TEMP_DIR', '/app/tmp')
else:
    app.config['MEDIA_DIR'] = os.path.join(os.path.dirname(__file__), 'media')
    app.config['TEMP_DIR'] = os.path.join(os.path.dirname(__file__), 'tmp')

# Ensure directories exist
os.makedirs(app.config['MEDIA_DIR'], exist_ok=True)
os.makedirs(app.config['TEMP_DIR'], exist_ok=True)
os.makedirs(os.path.join(app.config['MEDIA_DIR'], 'videos', 'scene', '720p30'), exist_ok=True)
os.makedirs(os.path.join(app.static_folder, 'videos'), exist_ok=True)


def sanitize_input(text):
    """Sanitize input text by removing extra whitespace and newlines"""
    return ' '.join(text.strip().split())

def sanitize_title(text):
    """Sanitize text for use in title"""
    text = sanitize_input(text)
    return text.replace('"', '').replace("'", "").strip()

# Load Manim documentation for AI reference
def load_manim_docs():
    """Load Manim documentation for AI reference"""
    try:
        docs_path = os.path.join(os.path.dirname(__file__), 'manim_docs.txt')
        if os.path.exists(docs_path):
            with open(docs_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning("manim_docs.txt not found. AI will work without documentation reference.")
            return ""
    except Exception as e:
        logger.error(f"Error loading Manim documentation: {str(e)}")
        return ""

# Load documentation at startup
MANIM_DOCS = load_manim_docs()

def get_relevant_docs(concept, max_chars=3000):
    """Extract relevant documentation sections based on the concept"""
    if not MANIM_DOCS:
        return ""
    
    concept_lower = concept.lower()
    relevant_sections = []
    
    # Split docs into sections
    sections = MANIM_DOCS.split('=' * 80)
    
    for section in sections:
        if any(keyword in section.lower() for keyword in [
            concept_lower, 'example', 'animation', 'color', 'text', 'scene',
            'create', 'write', 'play', 'wait'
        ]):
            relevant_sections.append(section[:1000])  # Limit each section
    
    # Combine and limit total length
    combined = '\n'.join(relevant_sections)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "..."
    
    return combined

def generate_manim_prompt(concept):
    """Generate a focused prompt for Gemini to create original Manim code"""
    
    # Simplified prompt to avoid token limits
    base_prompt = f"""Create a Manim animation to explain: {concept}

CRITICAL REQUIREMENTS:
- Use class MainScene(Scene):
- Never use MathTex indexing like eq[0].set_color()
- Use Text() and MathTex() for educational content
- Colors: "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFD93D"
- Include self.wait() between sections
- 60+ seconds total duration

STRUCTURE:
1. Title introduction (8s)
2. Problem setup (10s) 
3. Step-by-step solution (25s)
4. Visual demonstration (12s)
5. Summary (5s)

Generate complete working Python code."""

    return base_prompt

def generate_error_fallback(concept, error_msg):
    """Generate a simple error display scene when AI generation fails"""
    return f'''from manim import *

class MainScene(Scene):
    def construct(self):
        # Error in AI generation for: {concept}
        error_title = Text("Generation Error", font_size=48, color="#FF6B6B")
        error_title.to_edge(UP)
        
        concept_text = Text(f"Concept: {concept}", font_size=24, color="#FFFFFF")
        concept_text.next_to(error_title, DOWN, buff=0.8)
        
        error_detail = Text("Syntax Error Detected", font_size=32, color="#FFAA00")
        error_detail.next_to(concept_text, DOWN, buff=0.8)
        
        error_msg_text = Text(f"Error: {error_msg[:80]}...", font_size=18, color="#FFFFFF")
        error_msg_text.next_to(error_detail, DOWN, buff=0.5)
        
        retry_text = Text("Please try again with a different prompt", font_size=20, color="#4ECDC4")
        retry_text.next_to(error_msg_text, DOWN, buff=1.0)
        
        self.play(Write(error_title), run_time=2)
        self.play(Write(concept_text), run_time=1)
        self.play(Write(error_detail), run_time=1.5)
        self.play(Write(error_msg_text), run_time=2)
        self.play(Write(retry_text), run_time=1.5)
        self.wait(5)
'''

def select_template(concept):
    """Select appropriate template based on the concept."""
    concept = concept.lower().strip()
    
    # Define template mappings with keywords
    template_mappings = {
        'pythagorean': {
            'keywords': ['pythagoras', 'pythagorean', 'right triangle', 'hypotenuse'],
            'generator': generate_pythagorean_code
        },
        'quadratic': {
            'keywords': ['quadratic', 'parabola', 'x squared', 'x^2'],
            'generator': generate_quadratic_code
        },
        'trigonometry': {
            'keywords': ['sine', 'cosine', 'trigonometry', 'trig', 'unit circle'],
            'generator': generate_trig_code
        },
        '3d_surface': {
            'keywords': ['3d surface', 'surface plot', '3d plot', 'three dimensional'],
            'generator': generate_3d_surface_code
        },
        'sphere': {
            'keywords': ['sphere', 'ball', 'spherical'],
            'generator': generate_sphere_code
        },
        'cube': {
            'keywords': ['cube', 'cubic', 'box'],
            'generator': generate_cube_code
        },
        'derivative': {
            'keywords': ['derivative', 'differentiation', 'slope', 'rate of change'],
            'generator': generate_derivative_code
        },
        'integral': {
            'keywords': ['integration', 'integral', 'area under curve', 'antiderivative'],
            'generator': generate_integral_code
        },
        'matrix': {
            'keywords': ['matrix', 'matrices', 'linear transformation'],
            'generator': generate_matrix_code
        },
        'eigenvalue': {
            'keywords': ['eigenvalue', 'eigenvector', 'characteristic'],
            'generator': generate_eigenvalue_code
        },
        'complex': {
            'keywords': ['complex', 'imaginary', 'complex plane'],
            'generator': generate_complex_code
        },
        'differential_equation': {
            'keywords': ['differential equation', 'ode', 'pde'],
            'generator': generate_diff_eq_code
        }
    }
    
    # Find best matching template
    best_match = None
    max_matches = 0
    
    for template_name, template_info in template_mappings.items():
        matches = sum(1 for keyword in template_info['keywords'] if keyword in concept)
        if matches > max_matches:
            max_matches = matches
            best_match = template_info['generator']
    
    # Return best matching template or fallback to basic visualization
    if best_match and max_matches > 0:
        try:
            return best_match()
        except Exception as e:
            logger.error(f"Error generating template {best_match.__name__}: {str(e)}")
            return generate_basic_visualization_code()
    
    # Default to basic visualization if no good match found
    return generate_basic_visualization_code()

def generate_pythagorean_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Phase 1: Introduction (10 seconds)
        title = Text("The Pythagorean Theorem", font_size=48, color=YELLOW)
        subtitle = Text("One of Mathematics' Most Important Discoveries", font_size=24, color="#00FFFF")
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=3)
        self.play(Write(subtitle), run_time=2)
        self.wait(4)
        
        historical = Text("Discovered around 500 BC by Pythagoras", font_size=20, color=WHITE)
        historical.next_to(subtitle, DOWN, buff=0.5)
        self.play(Write(historical), run_time=2)
        self.wait(3)
        
        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(historical), run_time=2)
        
        # Phase 2: What is a right triangle? (12 seconds)
        definition_title = Text("What is a Right Triangle?", font_size=36, color=GREEN)
        self.play(Write(definition_title), run_time=2)
        self.wait(2)
        
        # Create and explain right triangle step by step
        axes = Axes(x_range=[0, 6], y_range=[0, 5], x_length=8, y_length=6)
        self.play(Create(axes), run_time=2)
        
        # Build triangle step by step
        point_a = Dot(axes.c2p(1, 1), color=YELLOW, radius=0.08)
        point_b = Dot(axes.c2p(4, 1), color=YELLOW, radius=0.08)
        point_c = Dot(axes.c2p(4, 4), color=YELLOW, radius=0.08)
        
        self.play(Create(point_a), run_time=1)
        a_label = Text("A", font_size=24, color=YELLOW).next_to(point_a, DL)
        self.play(Write(a_label), run_time=1)
        
        self.play(Create(point_b), run_time=1)
        b_label = Text("B", font_size=24, color=YELLOW).next_to(point_b, DR)
        self.play(Write(b_label), run_time=1)
        
        self.play(Create(point_c), run_time=1)
        c_label = Text("C", font_size=24, color=YELLOW).next_to(point_c, UR)
        self.play(Write(c_label), run_time=1)
        
        # Draw sides
        side_ab = Line(point_a.get_center(), point_b.get_center(), color=BLUE, stroke_width=4)
        side_bc = Line(point_b.get_center(), point_c.get_center(), color=RED, stroke_width=4)
        side_ac = Line(point_a.get_center(), point_c.get_center(), color=YELLOW, stroke_width=4)
        
        self.play(Create(side_ab), run_time=1.5)
        self.play(Create(side_bc), run_time=1.5)
        self.play(Create(side_ac), run_time=1.5)
        
        # Add right angle indicator
        right_angle = Square(side_length=0.3, color=GREEN).move_to(point_b.get_center() + UP*0.15 + LEFT*0.15)
        self.play(Create(right_angle), run_time=1)
        
        definition_text = Text("A triangle with one 90° angle", font_size=24, color=WHITE)
        definition_text.next_to(definition_title, DOWN, buff=1)
        self.play(Write(definition_text), run_time=2)
        self.wait(3)
        
        self.play(FadeOut(definition_title), FadeOut(definition_text), run_time=1)
        
        # Phase 3: Introducing the theorem (15 seconds)
        theorem_title = Text("The Pythagorean Theorem", font_size=32, color="#00FFFF")
        theorem_title.to_corner(UL)
        self.play(Write(theorem_title), run_time=2)
        
        # Label the sides properly
        side_a_label = Text("a = 3", font_size=28, color=BLUE)
        side_b_label = Text("b = 4", font_size=28, color=RED)
        side_c_label = Text("c = ?", font_size=28, color=YELLOW)
        
        side_a_label.next_to(side_ab, DOWN, buff=0.3)
        side_b_label.next_to(side_bc, RIGHT, buff=0.3)
        side_c_label.next_to(side_ac.get_center(), LEFT, buff=0.3)
        
        explanation1 = Text("In any right triangle:", font_size=24, color=WHITE)
        explanation2 = Text("• 'a' and 'b' are the legs (sides forming the right angle)", font_size=20, color=WHITE)
        explanation3 = Text("• 'c' is the hypotenuse (longest side, opposite right angle)", font_size=20, color=WHITE)
        
        explanations = VGroup(explanation1, explanation2, explanation3)
        explanations.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        explanations.next_to(theorem_title, DOWN, buff=0.5)
        
        self.play(Write(side_a_label), run_time=1.5)
        self.play(Write(explanation1), run_time=2)
        self.wait(2)
        
        self.play(Write(side_b_label), run_time=1.5)
        self.play(Write(explanation2), run_time=2)
        self.wait(2)
        
        self.play(Write(side_c_label), run_time=1.5)
        self.play(Write(explanation3), run_time=2)
        self.wait(3)
        
        # Phase 4: The actual theorem (12 seconds)
        self.play(FadeOut(explanations), run_time=1)
        
        theorem_statement = Text("The Theorem States:", font_size=28, color=GREEN)
        theorem_equation = Text("a² + b² = c²", font_size=40, color=WHITE)
        theorem_meaning = Text("The sum of squares of legs equals square of hypotenuse", font_size=18, color=GRAY)
        
        theorem_group = VGroup(theorem_statement, theorem_equation, theorem_meaning)
        theorem_group.arrange(DOWN, buff=0.4)
        theorem_group.next_to(theorem_title, DOWN, buff=0.5)
        
        self.play(Write(theorem_statement), run_time=2)
        self.wait(2)
        self.play(Write(theorem_equation), run_time=3)
        self.wait(2)
        self.play(Write(theorem_meaning), run_time=2)
        self.wait(3)
        
        # Phase 5: Step-by-step calculation (15 seconds)
        self.play(FadeOut(theorem_group), run_time=1)
        
        calc_title = Text("Let's Calculate c:", font_size=28, color=ORANGE)
        calc_title.next_to(theorem_title, DOWN, buff=0.5)
        self.play(Write(calc_title), run_time=2)
        
        # Detailed calculation steps
        step1 = Text("Step 1: Substitute known values", font_size=22, color=WHITE)
        step1_eq = Text("3² + 4² = c²", font_size=32, color=WHITE)
        
        step2 = Text("Step 2: Calculate the squares", font_size=22, color=WHITE)
        step2_show = Text("3² = 3 × 3 = 9", font_size=24, color=BLUE)
        step2_show2 = Text("4² = 4 × 4 = 16", font_size=24, color=RED)
        step2_eq = Text("9 + 16 = c²", font_size=32, color=WHITE)
        
        step3 = Text("Step 3: Add the results", font_size=22, color=WHITE)
        step3_eq = Text("25 = c²", font_size=32, color=WHITE)
        
        step4 = Text("Step 4: Take the square root", font_size=22, color=WHITE)
        step4_eq = Text("c = √25 = 5", font_size=32, color=YELLOW)
        
        steps_group = VGroup(step1, step1_eq, step2, step2_show, step2_show2, step2_eq, step3, step3_eq, step4, step4_eq)
        steps_group.arrange(DOWN, buff=0.3)
        steps_group.next_to(calc_title, DOWN, buff=0.5)
        
        # Animate each step
        self.play(Write(step1), run_time=1.5)
        self.play(Write(step1_eq), run_time=2)
        self.wait(2)
        
        self.play(Write(step2), run_time=1.5)
        self.play(Write(step2_show), run_time=1.5)
        self.play(Write(step2_show2), run_time=1.5)
        self.play(Write(step2_eq), run_time=2)
        self.wait(2)
        
        self.play(Write(step3), run_time=1.5)
        self.play(Write(step3_eq), run_time=2)
        self.wait(2)
        
        self.play(Write(step4), run_time=1.5)
        self.play(Write(step4_eq), run_time=2)
        
        # Update the triangle label
        new_c_label = Text("c = 5", font_size=28, color=YELLOW)
        new_c_label.move_to(side_c_label.get_center())
        self.play(Transform(side_c_label, new_c_label), run_time=2)
        self.wait(3)
        
        # Phase 6: Visual proof with squares (18 seconds)
        self.play(
            FadeOut(calc_title), FadeOut(steps_group), 
            FadeOut(axes), FadeOut(side_a_label), FadeOut(side_b_label), FadeOut(side_c_label),
            run_time=2
        )
        
        visual_title = Text("Visual Proof: Square Areas", font_size=32, color=PURPLE)
        visual_title.to_corner(UL)
        self.play(Write(visual_title), run_time=2)
        
        # Create new centered triangle
        triangle_center = ORIGIN
        triangle = Polygon(
            triangle_center + LEFT*1.5 + DOWN*1,
            triangle_center + RIGHT*1.5 + DOWN*1,
            triangle_center + RIGHT*1.5 + UP*2,
            color=WHITE, stroke_width=3
        )
        
        self.play(Create(triangle), run_time=2)
        
        # Create squares on each side
        square_a = Square(side_length=1.2, color=BLUE, fill_opacity=0.4)
        square_b = Square(side_length=1.6, color=RED, fill_opacity=0.4)
        square_c = Square(side_length=2.0, color=YELLOW, fill_opacity=0.4)
        
        square_a.next_to(triangle, DOWN, buff=0.1)
        square_b.next_to(triangle, RIGHT, buff=0.1)
        square_c.move_to(LEFT*4 + UP*1)
        
        explanation_squares = Text("Each side forms a square with area = side²", font_size=20, color=WHITE)
        explanation_squares.next_to(visual_title, DOWN, buff=0.5)
        self.play(Write(explanation_squares), run_time=2)
        self.wait(2)
        
        # Show squares one by one
        area_a = Text("Area = 3² = 9", font_size=20, color=BLUE)
        area_a.move_to(square_a.get_center())
        self.play(Create(square_a), Write(area_a), run_time=2)
        self.wait(2)
        
        area_b = Text("Area = 4² = 16", font_size=20, color=RED)
        area_b.move_to(square_b.get_center())
        self.play(Create(square_b), Write(area_b), run_time=2)
        self.wait(2)
        
        area_c = Text("Area = 5² = 25", font_size=20, color=YELLOW)
        area_c.move_to(square_c.get_center())
        self.play(Create(square_c), Write(area_c), run_time=2)
        self.wait(2)
        
        # Show the relationship
        final_eq = Text("9 + 16 = 25 ✓", font_size=36, color=GREEN)
        final_eq.next_to(explanation_squares, DOWN, buff=1)
        self.play(Write(final_eq), run_time=3)
        self.wait(3)
        
        # Phase 7: Applications and importance (10 seconds)
        self.play(FadeOut(VGroup(visual_title, explanation_squares, triangle, square_a, square_b, square_c, area_a, area_b, area_c, final_eq)), run_time=2)
        
        applications_title = Text("Real-World Applications", font_size=32, color=GREEN)
        self.play(Write(applications_title), run_time=2)
        
        apps = VGroup(
            Text("• Construction and Architecture", font_size=20, color=WHITE),
            Text("• Navigation and GPS Systems", font_size=20, color=WHITE),
            Text("• Computer Graphics and Gaming", font_size=20, color=WHITE),
            Text("• Physics and Engineering", font_size=20, color=WHITE),
            Text("• Distance calculations in coordinate geometry", font_size=20, color=WHITE)
        )
        apps.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        apps.next_to(applications_title, DOWN, buff=0.5)
        
        for app in apps:
            self.play(Write(app), run_time=1.5)
            self.wait(1)
        
        self.wait(3)
        
        # Phase 8: Final summary (8 seconds)
        self.play(FadeOut(applications_title), FadeOut(apps), run_time=1)
        
        summary_title = Text("Summary", font_size=36, color=YELLOW)
        summary_points = VGroup(
            Text("✓ Pythagorean theorem: a² + b² = c²", font_size=24, color=WHITE),
            Text("✓ Only works for right triangles", font_size=24, color=WHITE),
            Text("✓ Fundamental tool in mathematics", font_size=24, color=WHITE)
        )
        summary_points.arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        summary_points.next_to(summary_title, DOWN, buff=0.5)
        
        self.play(Write(summary_title), run_time=2)
        for point in summary_points:
            self.play(Write(point), run_time=1.5)
        
        self.wait(4)'''

def generate_derivative_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Introduction phase (4 seconds)
        title = Text("Understanding Derivatives", font_size=48, color=YELLOW)
        subtitle = Text("The Slope of a Function", font_size=32, color="#00FFFF")
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=2)
        self.play(Write(subtitle), run_time=1.5)
        self.wait(2)
        
        # Clear and setup phase (3 seconds)
        self.play(FadeOut(title), FadeOut(subtitle))
        
        # Create coordinate system
        axes = Axes(
            x_range=[-3, 3, 1], y_range=[-1, 3, 1],
            x_length=10, y_length=6,
            axis_config={"include_tip": True}
        )
        
        # Add labels
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)
        
        self.play(Create(axes), Write(x_label), Write(y_label), run_time=2)
        self.wait(1)
        
        # Show function phase (4 seconds)
        def func(x):
            return 0.3 * x**2 + 0.5
            
        graph = axes.plot(func, color=BLUE, x_range=[-2.5, 2.5])
        func_label = Text("f(x) = x²", font_size=32, color=BLUE)
        func_label.to_corner(UL)
        
        self.play(Create(graph), run_time=2)
        self.play(Write(func_label), run_time=1.5)
        self.wait(2)
        
        # Explain derivative concept (5 seconds)
        concept_text = Text("Derivative = Rate of Change = Slope", font_size=28, color="#00FFFF")
        concept_text.next_to(func_label, DOWN, buff=0.5)
        
        self.play(Write(concept_text), run_time=2)
        self.wait(3)
        
        # Show tangent line at a point (6 seconds)
        x_val = 1.5
        point = Dot(axes.c2p(x_val, func(x_val)), color=YELLOW, radius=0.08)
        point_label = Text(f"Point: ({x_val}, {func(x_val):.1f})", font_size=24, color=YELLOW)
        point_label.next_to(point, UR, buff=0.3)
        
        # Calculate derivative at this point (for x², derivative is 2x)
        slope = 2 * 0.3 * x_val  # derivative of 0.3x² is 0.6x
        
        # Create tangent line
        tangent_line = axes.plot(
            lambda x: slope * (x - x_val) + func(x_val),
            color=RED, x_range=[x_val-1, x_val+1]
        )
        
        self.play(Create(point), Write(point_label), run_time=2)
        self.play(Create(tangent_line), run_time=2)
        
        tangent_label = Text(f"Tangent Line (slope = {slope:.1f})", font_size=24, color=RED)
        tangent_label.next_to(concept_text, DOWN, buff=0.3)
        self.play(Write(tangent_label), run_time=1.5)
        self.wait(2)
        
        # Show derivative formula (4 seconds)
        self.play(FadeOut(point_label), FadeOut(tangent_label))
        
        derivative_title = Text("Derivative Formula:", font_size=32, color=GREEN)
        derivative_formula = Text("f'(x) = lim[h→0] [f(x+h) - f(x)] / h", font_size=28, color=WHITE)
        derivative_title.next_to(concept_text, DOWN, buff=0.5)
        derivative_formula.next_to(derivative_title, DOWN, buff=0.3)
        
        self.play(Write(derivative_title), run_time=1.5)
        self.play(Write(derivative_formula), run_time=2)
        self.wait(2)
        
        # Calculate specific derivative (5 seconds)
        calc_title = Text("For f(x) = x²:", font_size=28, color=ORANGE)
        calc_step1 = Text("f'(x) = 2x", font_size=32, color=WHITE)
        calc_step2 = Text(f"At x = {x_val}: f'({x_val}) = 2({x_val}) = {2*x_val}", font_size=28, color=YELLOW)
        
        calc_group = VGroup(calc_title, calc_step1, calc_step2)
        calc_group.arrange(DOWN, buff=0.3)
        calc_group.next_to(derivative_formula, DOWN, buff=0.5)
        
        for calc in calc_group:
            self.play(Write(calc), run_time=1.5)
            self.wait(1)
        
        # Animate moving point to show changing slope (6 seconds)
        moving_text = Text("Watch how the slope changes!", font_size=28, color=PURPLE)
        moving_text.to_corner(DR)
        self.play(Write(moving_text), run_time=1.5)
        
        # Create moving elements
        moving_point = Dot(color=YELLOW, radius=0.08)
        moving_tangent = Line(color=RED)
        slope_text = Text("", font_size=24, color=RED)
        
        def update_tangent(mob):
            x = moving_point.get_center()[0] / axes.x_axis.unit_size
            y = func(x)
            slope_val = 2 * 0.3 * x
            
            # Update tangent line
            start_x = x - 0.8
            end_x = x + 0.8
            start_point = axes.c2p(start_x, slope_val * (start_x - x) + y)
            end_point = axes.c2p(end_x, slope_val * (end_x - x) + y)
            mob.put_start_and_end_on(start_point, end_point)
            
        def update_slope_text(mob):
            x = moving_point.get_center()[0] / axes.x_axis.unit_size
            slope_val = 2 * 0.3 * x
            mob.become(Text(f"Slope = {slope_val:.1f}", font_size=24, color=RED))
            mob.next_to(moving_point, UR, buff=0.3)
        
        moving_tangent.add_updater(update_tangent)
        slope_text.add_updater(update_slope_text)
        
        # Start animation
        moving_point.move_to(axes.c2p(-2, func(-2)))
        self.add(moving_point, moving_tangent, slope_text)
        
        self.play(
            moving_point.animate.move_to(axes.c2p(2, func(2))),
            run_time=4,
            rate_func=smooth
        )
        self.wait(2)
        
        # Final summary (3 seconds)
        summary = Text("Derivative = Instantaneous Rate of Change", font_size=32, color=GREEN)
        summary.move_to(DOWN * 3)
        self.play(Write(summary), run_time=2)
        self.wait(3)'''

def generate_integral_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Introduction phase (4 seconds)
        title = Text("Understanding Integration", font_size=44, color=YELLOW)
        subtitle = Text("Area Under the Curve", font_size=28, color="#00FFFF")
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=2)
        self.play(Write(subtitle), run_time=1.5)
        self.wait(2)
        
        # Clear and setup phase (3 seconds)
        self.play(FadeOut(title), FadeOut(subtitle))
        
        # Create coordinate system
        axes = Axes(
            x_range=[-1, 4, 1], y_range=[-1, 3, 1],
            x_length=10, y_length=6,
            axis_config={"include_tip": True}
        )
        
        # Add labels
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)
        
        self.play(Create(axes), Write(x_label), Write(y_label), run_time=2)
        self.wait(1)
        
        # Show the function (4 seconds)
        def func(x):
            return 0.3 * x**2 + 0.5
            
        graph = axes.plot(func, color=BLUE, x_range=[-0.5, 3.5])
        func_label = Text("f(x) = x²", font_size=32, color=BLUE)
        func_label.to_corner(UL)
        
        self.play(Create(graph), run_time=2)
        self.play(Write(func_label), run_time=1.5)
        self.wait(2)
        
        # Explain the concept (4 seconds)
        concept_title = Text("Integration Concept:", font_size=28, color=GREEN)
        concept_text = Text("Find the area under the curve", font_size=24, color=WHITE)
        concept_title.next_to(func_label, DOWN, buff=0.5)
        concept_text.next_to(concept_title, DOWN, buff=0.3)
        
        self.play(Write(concept_title), run_time=1.5)
        self.play(Write(concept_text), run_time=2)
        self.wait(2)
        
        # Show interval (3 seconds)
        interval_text = Text("From x = 0 to x = 2", font_size=24, color=ORANGE)
        interval_text.next_to(concept_text, DOWN, buff=0.3)
        
        # Add vertical lines at boundaries
        left_line = DashedLine(
            start=axes.c2p(0, 0), end=axes.c2p(0, func(0)),
            color=ORANGE, stroke_width=3
        )
        right_line = DashedLine(
            start=axes.c2p(2, 0), end=axes.c2p(2, func(2)),
            color=ORANGE, stroke_width=3
        )
        
        self.play(Write(interval_text), run_time=1)
        self.play(Create(left_line), Create(right_line), run_time=2)
        self.wait(1)
        
        # Riemann sum approximation (6 seconds)
        riemann_title = Text("Riemann Sum Approximation", font_size=24, color=PURPLE)
        riemann_title.next_to(interval_text, DOWN, buff=0.5)
        self.play(Write(riemann_title), run_time=1.5)
        
        # Show rectangles with increasing subdivisions
        n_values = [4, 8, 16]
        colors = [RED, GREEN, YELLOW]
        
        for i, (n, color) in enumerate(zip(n_values, colors)):
            rects = VGroup()
            dx = 2 / n
            
            for j in range(n):
                x_left = j * dx
                x_right = (j + 1) * dx
                height = func(x_left)  # Left Riemann sum
                
                rect = Rectangle(
                    width=dx * axes.x_axis.unit_size,
                    height=height * axes.y_axis.unit_size,
                    color=color,
                    fill_opacity=0.4,
                    stroke_width=1
                )
                rect.move_to(axes.c2p(x_left + dx/2, height/2))
                rects.add(rect)
            
            n_text = Text(f"n = {n} rectangles", font_size=20, color=color)
            n_text.next_to(riemann_title, DOWN, buff=0.3 + i*0.3)
            
            if i == 0:
                self.play(Create(rects), Write(n_text), run_time=2)
            else:
                self.play(
                    Transform(prev_rects, rects),
                    Transform(prev_n_text, n_text),
                    run_time=1.5
                )
            
            prev_rects = rects
            prev_n_text = n_text
            self.wait(1)
        
        # Show exact area (5 seconds)
        self.play(FadeOut(prev_rects), FadeOut(prev_n_text))
        
        exact_title = Text("Exact Area (Limit as n → ∞)", font_size=24, color="#00FFFF")
        exact_title.move_to(riemann_title.get_center())
        
        # Create smooth area
        area = axes.get_area(
            graph,
            x_range=[0, 2],
            color="#00FFFF",
            opacity=0.6
        )
        
        self.play(Write(exact_title), run_time=1.5)
        self.play(FadeIn(area), run_time=2)
        self.wait(2)
        
        # Show the calculation (5 seconds)
        calc_title = Text("Calculation:", font_size=28, color=WHITE)
        integral_notation = Text("∫₀² x² dx", font_size=32, color=WHITE)
        calc_title.next_to(exact_title, DOWN, buff=0.8)
        integral_notation.next_to(calc_title, DOWN, buff=0.3)
        
        self.play(Write(calc_title), run_time=1)
        self.play(Write(integral_notation), run_time=1.5)
        
        # Step by step solution
        step1 = Text("= [x³/3]₀²", font_size=28, color=WHITE)
        step2 = Text("= 2³/3 - 0³/3", font_size=28, color=WHITE)
        step3 = Text("= 8/3 - 0", font_size=28, color=WHITE)
        step4 = Text("= 8/3 ≈ 2.67", font_size=28, color=YELLOW)
        
        steps = VGroup(step1, step2, step3, step4)
        steps.arrange(DOWN, buff=0.2)
        steps.next_to(integral_notation, DOWN, buff=0.3)
        
        for step in steps:
            self.play(Write(step), run_time=1)
            self.wait(0.5)
        
        # Fundamental Theorem of Calculus (4 seconds)
        self.play(
            FadeOut(calc_title), FadeOut(integral_notation), FadeOut(steps)
        )
        
        ftc_title = Text("Fundamental Theorem of Calculus", font_size=24, color=GREEN)
        ftc_content = Text("∫ f'(x) dx = f(x) + C", font_size=28, color=WHITE)
        ftc_explanation = Text("Integration is the reverse of differentiation!", font_size=20, color=GREEN)
        
        ftc_group = VGroup(ftc_title, ftc_content, ftc_explanation)
        ftc_group.arrange(DOWN, buff=0.3)
        ftc_group.move_to(DOWN * 2)
        
        for item in ftc_group:
            self.play(Write(item), run_time=1.2)
        
        self.wait(2)
        
        # Final summary (3 seconds)
        summary = Text("Integration: Finding areas and accumulation!", font_size=28, color=YELLOW)
        summary.move_to(DOWN * 3.5)
        self.play(Write(summary), run_time=2)
        self.wait(3)'''

def generate_3d_surface_code():
    return '''from manim import *
import numpy as np

class MainScene(ThreeDScene):
    def construct(self):
        # Introduction phase (4 seconds)
        title = Text("3D Surface Visualization", font_size=44, color=YELLOW)
        subtitle = Text("z = sin(x) × cos(y)", font_size=28, color=CYAN)
        
        # Position text for 3D scene
        title.rotate(PI/2, axis=RIGHT).move_to(OUT*2 + UP*2)
        subtitle.rotate(PI/2, axis=RIGHT).move_to(OUT*2 + UP*1)
        
        self.add_fixed_in_frame_mobjects(title, subtitle)
        
        self.play(Write(title), run_time=2)
        self.play(Write(subtitle), run_time=1.5)
        self.wait(2)
        
        # Clear and setup phase (3 seconds)
        self.play(FadeOut(title), FadeOut(subtitle))
        
        # Set up the 3D scene
        self.set_camera_orientation(
            phi=60 * DEGREES,
            theta=45 * DEGREES,
            zoom=0.8
        )
        
        # Create 3D axes with better spacing
        axes = ThreeDAxes(
            x_range=[-3, 3, 1],
            y_range=[-3, 3, 1], 
            z_range=[-2, 2, 0.5],
            x_length=6,
            y_length=6,
            z_length=4,
            axis_config={"include_tip": True}
        )
        
        # Add axis labels
        x_label = Text("x", font_size=24, color=RED)
        y_label = Text("y", font_size=24, color=GREEN)
        z_label = Text("z", font_size=24, color=BLUE)
        
        x_label.next_to(axes.x_axis.get_end(), RIGHT)
        y_label.next_to(axes.y_axis.get_end(), UP)
        z_label.next_to(axes.z_axis.get_end(), OUT)
        
        self.play(Create(axes), run_time=2)
        self.play(Write(x_label), Write(y_label), Write(z_label), run_time=1.5)
        self.wait(1)
        
        # Explain the function (4 seconds)
        func_explanation = Text("Function: z = sin(x) × cos(y)", font_size=24, color=WHITE)
        func_explanation.to_corner(UL)
        self.add_fixed_in_frame_mobjects(func_explanation)
        
        properties = VGroup(
            Text("• Periodic in both x and y directions", font_size=16, color=GRAY),
            Text("• Range: [-1, 1]", font_size=16, color=GRAY),
            Text("• Creates wave patterns", font_size=16, color=GRAY)
        )
        properties.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        properties.next_to(func_explanation, DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(properties)
        
        self.play(Write(func_explanation), run_time=2)
        for prop in properties:
            self.play(Write(prop), run_time=0.8)
        self.wait(1)
        
        # Create surface function
        def surface_func(u, v):
            x = u
            y = v
            z = np.sin(u) * np.cos(v)
            return np.array([x, y, z])
        
        # Build surface progressively (6 seconds)
        building_text = Text("Building the surface...", font_size=20, color=YELLOW)
        building_text.to_corner(UR)
        self.add_fixed_in_frame_mobjects(building_text)
        self.play(Write(building_text), run_time=1)
        
        # Create surface with optimized resolution
        surface = Surface(
            lambda u, v: surface_func(u, v),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=(24, 24),
            should_make_jagged=False,
            stroke_opacity=0.3
        )
        
        # Add gradient coloring
        surface.set_style(
            fill_opacity=0.8,
            stroke_color=WHITE,
            stroke_width=0.5
        )
        surface.set_fill_by_value(
            axes=axes,
            colors=[(RED, -1), (YELLOW, 0), (BLUE, 1)],
            axis=2
        )
        
        self.play(Create(surface), run_time=4)
        self.play(FadeOut(building_text), run_time=1)
        self.wait(1)
        
        # Show cross-sections (5 seconds)
        cross_section_text = Text("Cross-sections reveal wave patterns", font_size=18, color=ORANGE)
        cross_section_text.to_corner(UR)
        self.add_fixed_in_frame_mobjects(cross_section_text)
        self.play(Write(cross_section_text), run_time=1.5)
        
        # Create cross-section at y=0
        y0_plane = Rectangle(
            width=6, height=4,
            fill_color=GREEN, fill_opacity=0.3,
            stroke_color=GREEN, stroke_width=2
        )
        y0_plane.rotate(PI/2, axis=UP)
        
        # Cross-section curve
        cross_curve = ParametricFunction(
            lambda t: np.array([t, 0, np.sin(t)]),
            t_range=[-3, 3],
            color=GREEN,
            stroke_width=4
        )
        
        self.play(Create(y0_plane), run_time=1.5)
        self.play(Create(cross_curve), run_time=2)
        self.wait(1)
        
        # Rotate camera to show different perspectives (6 seconds)
        self.play(FadeOut(cross_section_text), FadeOut(properties))
        
        rotation_text = Text("Exploring different angles...", font_size=18, color=PURPLE)
        rotation_text.to_corner(UR)
        self.add_fixed_in_frame_mobjects(rotation_text)
        self.play(Write(rotation_text), run_time=1)
        
        # Start ambient rotation
        self.begin_ambient_camera_rotation(rate=0.3)
        
        # Move camera through different positions
        self.move_camera(phi=75*DEGREES, theta=30*DEGREES, run_time=2)
        self.wait(1)
        self.move_camera(phi=45*DEGREES, theta=-30*DEGREES, run_time=2)
        self.wait(1)
        
        self.stop_ambient_camera_rotation()
        
        # Show level curves (4 seconds)
        self.play(FadeOut(rotation_text), FadeOut(y0_plane), FadeOut(cross_curve))
        
        level_text = Text("Level curves (contour lines)", font_size=18, color="#00FFFF")
        level_text.to_corner(UR)
        self.add_fixed_in_frame_mobjects(level_text)
        self.play(Write(level_text), run_time=1)
        
        # Create level curves at different z values
        level_values = [-0.8, -0.4, 0, 0.4, 0.8]
        level_colors = [RED, ORANGE, WHITE, LIGHT_GREEN, BLUE]
        
        level_curves = VGroup()
        for z_val, color in zip(level_values, level_colors):
            # Project level curves onto z=z_val plane
            for i in range(-2, 3):
                curve = ParametricFunction(
                    lambda t, z=z_val, offset=i: np.array([
                        t, 
                        offset * PI/2 if abs(np.sin(t)) >= abs(z_val) else None,
                        z_val
                    ]) if abs(np.sin(t)) >= abs(z_val) else None,
                    t_range=[-3, 3],
                    color=color,
                    stroke_width=2
                )
                if curve.get_num_points() > 0:
                    level_curves.add(curve)
        
        self.play(Create(level_curves), run_time=2)
        self.wait(2)
        
        # Final mathematical insights (4 seconds)
        self.play(FadeOut(level_text), FadeOut(level_curves))
        
        insights_title = Text("Mathematical Insights", font_size=20, color=YELLOW)
        insights_title.to_corner(UL)
        self.add_fixed_in_frame_mobjects(insights_title)
        
        insights = VGroup(
            Text("• Product of periodic functions", font_size=14, color=WHITE),
            Text("• Creates interference patterns", font_size=14, color=WHITE), 
            Text("• Maximum at (π/2, 0), (3π/2, π), etc.", font_size=14, color=WHITE),
            Text("• Used in wave mechanics & signal processing", font_size=14, color=WHITE)
        )
        insights.arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        insights.next_to(insights_title, DOWN, buff=0.2)
        self.add_fixed_in_frame_mobjects(insights)
        
        self.play(Write(insights_title), run_time=1)
        for insight in insights:
            self.play(Write(insight), run_time=0.8)
        
        # Final rotation (3 seconds)
        final_text = Text("Beautiful mathematics in 3D!", font_size=18, color=GREEN)
        final_text.to_corner(DR)
        self.add_fixed_in_frame_mobjects(final_text)
        
        self.play(Write(final_text), run_time=1)
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(3)
        self.stop_ambient_camera_rotation()'''

def generate_sphere_code():
    return '''from manim import *

class MainScene(ThreeDScene):
    def construct(self):
        # Set up the scene
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        axes = ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[-3, 3],
            x_length=6,
            y_length=6,
            z_length=6
        )
        
        # Create sphere
        radius = 2
        sphere = Surface(
            lambda u, v: np.array([
                radius * np.cos(u) * np.cos(v),
                radius * np.cos(u) * np.sin(v),
                radius * np.sin(u)
            ]),
            u_range=[-PI/2, PI/2],
            v_range=[0, TAU],
            checkerboard_colors=[BLUE_D, BLUE_E],
            resolution=(15, 32)
        )
        
        # Create radius line and label
        radius_line = Line3D(
            start=ORIGIN,
            end=[radius, 0, 0],
            color=YELLOW
        )
        r_label = Text("r", font_size=36).set_color(YELLOW)
        r_label.rotate(PI/2, RIGHT)
        r_label.next_to(radius_line, UP)
        
        # Create volume formula
        volume_formula = Text(
            "V = \\frac{4}{3}\\pi r^3"
        ).to_corner(UL)
        
        # Add everything to scene
        self.add(axes)
        self.play(Create(sphere))
        self.wait()
        self.play(Create(radius_line), Write(r_label))
        self.wait()
        self.play(Write(volume_formula))
        self.wait()
        
        # Rotate camera for better view
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
        self.stop_ambient_camera_rotation()'''

def generate_cube_code():
    return '''from manim import *

class MainScene(ThreeDScene):
    def construct(self):
        # Set up the scene
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        axes = ThreeDAxes(
            x_range=[-3, 3],
            y_range=[-3, 3],
            z_range=[-3, 3]
        )
        
        # Create cube
        cube = Cube(side_length=2, fill_opacity=0.7, stroke_width=2)
        cube.set_color(BLUE)
        
        # Labels for sides
        a_label = Text("a", font_size=36).set_color(YELLOW)
        a_label.next_to(cube, RIGHT)
        
        # Surface area formula
        area_formula = Text(
            "A = 6a^2"
        ).to_corner(UL)
        
        # Add everything to scene
        self.add(axes)
        self.play(Create(cube))
        self.wait()
        self.play(Write(a_label))
        self.wait()
        self.play(Write(area_formula))
        self.wait()
        
        # Rotate camera for better view
        self.begin_ambient_camera_rotation(rate=0.2)
        self.wait(5)
        self.stop_ambient_camera_rotation()'''

def generate_matrix_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Create matrices
        matrix_a = VGroup(
            Text("2  1"),
            Text("1  3")
        ).arrange(DOWN)
        matrix_a.add(SurroundingRectangle(matrix_a))
        
        matrix_b = VGroup(
            Text("1"),
            Text("2")
        ).arrange(DOWN)
        matrix_b.add(SurroundingRectangle(matrix_b))
        
        # Create multiplication symbol and equals sign
        times = Text("×")
        equals = Text("=")
        
        # Create result matrix
        result = VGroup(
            Text("4"),
            Text("7")
        ).arrange(DOWN)
        result.add(SurroundingRectangle(result))
        
        # Position everything
        equation = VGroup(
            matrix_a, times, matrix_b,
            equals, result
        ).arrange(RIGHT)
        
        # Create step-by-step calculations
        calc1 = Text("= [2(1) + 1(2)]")
        calc2 = Text("= [2 + 2]")
        calc3 = Text("= [4]")
        
        calcs = VGroup(calc1, calc2, calc3).arrange(DOWN)
        calcs.next_to(equation, DOWN, buff=1)
        
        # Create animations
        self.play(Create(matrix_a))
        self.play(Create(matrix_b))
        self.play(Write(times), Write(equals))
        self.play(Create(result))
        self.wait()
        
        self.play(Write(calc1))
        self.play(Write(calc2))
        self.play(Write(calc3))
        self.wait()'''

def generate_eigenvalue_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Create matrix and vector
        matrix = VGroup(
            Text("2  1"),
            Text("1  2")
        ).arrange(DOWN)
        matrix.add(SurroundingRectangle(matrix))
        
        vector = VGroup(
            Text("v₁"),
            Text("v₂")
        ).arrange(DOWN)
        vector.add(SurroundingRectangle(vector))
        
        # Create lambda and equation
        lambda_text = Text("λ")
        equation = Text("Av = λv")
        
        # Position everything
        group = VGroup(matrix, vector, lambda_text, equation).arrange(RIGHT)
        group.to_edge(UP)
        
        # Create characteristic equation steps
        char_eq = Text("det(A - λI) = 0")
        expanded = Text("|2-λ  1|")
        expanded2 = Text("|1  2-λ|")
        solved = Text("(2-λ)² - 1 = 0")
        result = Text("λ = 1, 3")
        
        # Position steps
        steps = VGroup(
            char_eq, expanded, expanded2,
            solved, result
        ).arrange(DOWN)
        steps.next_to(group, DOWN, buff=1)
        
        # Create animations
        self.play(Create(matrix), Create(vector))
        self.play(Write(lambda_text), Write(equation))
        self.wait()
        
        self.play(Write(char_eq))
        self.play(Write(expanded), Write(expanded2))
        self.play(Write(solved))
        self.play(Write(result))
        self.wait()'''

def generate_complex_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Phase 1: Introduction to Complex Numbers (12 seconds)
        title = Text("Complex Numbers", font_size=48, color=YELLOW)
        subtitle = Text("Extending the Real Number System", font_size=28, color="#00FFFF")
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=3)
        self.play(Write(subtitle), run_time=2)
        self.wait(3)
        
        # Historical context
        history = Text("Introduced in the 16th century to solve polynomial equations", font_size=20, color=WHITE)
        history.next_to(subtitle, DOWN, buff=0.5)
        self.play(Write(history), run_time=2)
        self.wait(2)
        
        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(history), run_time=2)
        
        # Phase 2: The Problem with Square Roots (10 seconds)
        problem_title = Text("The Problem: √(-1) = ?", font_size=36, color=RED)
        self.play(Write(problem_title), run_time=2)
        self.wait(2)
        
        problem_explanation = VGroup(
            Text("We know that:", font_size=24, color=WHITE),
            Text("• 2² = 4, so √4 = 2", font_size=20, color=WHITE),
            Text("• (-2)² = 4, so √4 = -2", font_size=20, color=WHITE),
            Text("• But what about √(-4)?", font_size=20, color=RED),
            Text("• No real number squared gives -4!", font_size=20, color=RED)
        )
        problem_explanation.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        problem_explanation.next_to(problem_title, DOWN, buff=0.5)
        
        for line in problem_explanation:
            self.play(Write(line), run_time=1.5)
            self.wait(1)
        
        self.wait(2)
        self.play(FadeOut(problem_title), FadeOut(problem_explanation), run_time=2)
        
        # Phase 3: Introduction of i (8 seconds)
        solution_title = Text("The Solution: The Imaginary Unit 'i'", font_size=32, color=GREEN)
        self.play(Write(solution_title), run_time=2)
        
        i_definition = VGroup(
            Text("Define: i = √(-1)", font_size=36, color=YELLOW),
            Text("Therefore: i² = -1", font_size=32, color=YELLOW),
            Text("This allows us to work with square roots of negative numbers", font_size=20, color=WHITE)
        )
        i_definition.arrange(DOWN, buff=0.4)
        i_definition.next_to(solution_title, DOWN, buff=0.5)
        
        for line in i_definition:
            self.play(Write(line), run_time=2)
            self.wait(1)
        
        self.wait(2)
        self.play(FadeOut(solution_title), FadeOut(i_definition), run_time=2)
        
        # Phase 4: Standard Form of Complex Numbers (12 seconds)
        form_title = Text("Standard Form: a + bi", font_size=36, color="#00FFFF")
        self.play(Write(form_title), run_time=2)
        
        # Create visual representation
        form_explanation = VGroup(
            Text("Where:", font_size=24, color=WHITE),
            Text("• a = real part (real number)", font_size=20, color=BLUE),
            Text("• b = imaginary coefficient (real number)", font_size=20, color=RED),
            Text("• i = imaginary unit (√(-1))", font_size=20, color=YELLOW)
        )
        form_explanation.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        form_explanation.next_to(form_title, DOWN, buff=0.5)
        
        for line in form_explanation:
            self.play(Write(line), run_time=1.5)
            self.wait(1)
        
        # Examples
        examples_title = Text("Examples:", font_size=24, color=WHITE)
        examples = VGroup(
            Text("3 + 4i  (a=3, b=4)", font_size=20, color=WHITE),
            Text("2 - 5i  (a=2, b=-5)", font_size=20, color=WHITE),
            Text("7 + 0i = 7  (purely real)", font_size=20, color=BLUE),
            Text("0 + 3i = 3i  (purely imaginary)", font_size=20, color=RED)
        )
        examples.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        examples.next_to(form_explanation, DOWN, buff=0.5)
        
        self.play(Write(examples_title), run_time=1)
        for example in examples:
            self.play(Write(example), run_time=1.5)
            self.wait(1)
        
        self.wait(2)
        self.play(FadeOut(form_title), FadeOut(form_explanation), FadeOut(examples_title), FadeOut(examples), run_time=2)
        
        # Phase 5: The Complex Plane (15 seconds)
        plane_title = Text("The Complex Plane", font_size=36, color=PURPLE)
        plane_title.to_corner(UL)
        self.play(Write(plane_title), run_time=2)
        
        # Create coordinate system
        plane = ComplexPlane(
            x_range=[-4, 4, 1], y_range=[-3, 3, 1],
            x_length=8, y_length=6,
            axis_config={"include_tip": True}
        )
        
        # Label axes
        real_label = Text("Real Axis", font_size=20, color=BLUE)
        imag_label = Text("Imaginary Axis", font_size=20, color=RED)
        real_label.next_to(plane.x_axis.get_end(), DOWN)
        imag_label.next_to(plane.y_axis.get_end(), LEFT)
        
        self.play(Create(plane), run_time=3)
        self.play(Write(real_label), Write(imag_label), run_time=2)
        
        # Plot some complex numbers
        z1 = 3 + 2j
        z2 = -2 + 1j
        z3 = 1 - 2j
        
        dot1 = Dot(plane.n2p(z1), color=YELLOW, radius=0.08)
        dot2 = Dot(plane.n2p(z2), color=GREEN, radius=0.08)
        dot3 = Dot(plane.n2p(z3), color=ORANGE, radius=0.08)
        
        vector1 = Arrow(plane.n2p(0), plane.n2p(z1), color=YELLOW, buff=0)
        vector2 = Arrow(plane.n2p(0), plane.n2p(z2), color=GREEN, buff=0)
        vector3 = Arrow(plane.n2p(0), plane.n2p(z3), color=ORANGE, buff=0)
        
        label1 = Text("3 + 2i", font_size=18, color=YELLOW).next_to(dot1, UR)
        label2 = Text("-2 + i", font_size=18, color=GREEN).next_to(dot2, UL)
        label3 = Text("1 - 2i", font_size=18, color=ORANGE).next_to(dot3, DR)
        
        explanation_plane = Text("Each complex number is a point in the plane", font_size=20, color=WHITE)
        explanation_plane.next_to(plane_title, DOWN, buff=0.3)
        self.play(Write(explanation_plane), run_time=2)
        
        self.play(Create(vector1), Create(dot1), Write(label1), run_time=1.5)
        self.wait(1)
        self.play(Create(vector2), Create(dot2), Write(label2), run_time=1.5)
        self.wait(1)
        self.play(Create(vector3), Create(dot3), Write(label3), run_time=1.5)
        self.wait(2)
        
        # Phase 6: Basic Operations - Addition (12 seconds)
        self.play(
            FadeOut(vector2), FadeOut(vector3), FadeOut(dot2), FadeOut(dot3),
            FadeOut(label2), FadeOut(label3), FadeOut(explanation_plane), run_time=2
        )
        
        addition_title = Text("Addition of Complex Numbers", font_size=28, color=GREEN)
        addition_title.next_to(plane_title, DOWN, buff=0.3)
        self.play(Write(addition_title), run_time=2)
        
        # Show addition visually with two complex numbers
        w = 1 + 2j
        dot_w = Dot(plane.n2p(w), color=RED, radius=0.08)
        vector_w = Arrow(plane.n2p(0), plane.n2p(w), color=RED, buff=0)
        label_w = Text("w = 1 + 2i", font_size=18, color=RED).next_to(dot_w, UL)
        
        self.play(Create(vector_w), Create(dot_w), Write(label_w), run_time=2)
        
        # Show the addition rule
        addition_rule = Text("(a + bi) + (c + di) = (a + c) + (b + d)i", font_size=22, color=WHITE)
        addition_rule.next_to(addition_title, DOWN, buff=0.5)
        self.play(Write(addition_rule), run_time=2)
        
        # Calculate and show result
        z_sum = z1 + w
        dot_sum = Dot(plane.n2p(z_sum), color=PURPLE, radius=0.1)
        vector_sum = Arrow(plane.n2p(0), plane.n2p(z_sum), color=PURPLE, buff=0, stroke_width=6)
        
        # Show parallelogram rule
        parallel1 = DashedLine(plane.n2p(z1), plane.n2p(z_sum), color=GRAY)
        parallel2 = DashedLine(plane.n2p(w), plane.n2p(z_sum), color=GRAY)
        
        self.play(Create(parallel1), Create(parallel2), run_time=1.5)
        self.play(Create(vector_sum), Create(dot_sum), run_time=1.5)
        
        addition_result = Text("z + w = (3+1) + (2+2)i = 4 + 4i", font_size=20, color=PURPLE)
        addition_result.next_to(addition_rule, DOWN, buff=0.3)
        self.play(Write(addition_result), run_time=2)
        self.wait(3)
        
        # Phase 7: Multiplication and Powers of i (15 seconds)
        self.play(
            FadeOut(addition_title), FadeOut(addition_rule), FadeOut(addition_result),
            FadeOut(vector_w), FadeOut(dot_w), FadeOut(label_w),
            FadeOut(vector_sum), FadeOut(dot_sum), FadeOut(parallel1), FadeOut(parallel2), run_time=2
        )
        
        mult_title = Text("Powers of i - A Special Pattern", font_size=28, color=ORANGE)
        mult_title.next_to(plane_title, DOWN, buff=0.3)
        self.play(Write(mult_title), run_time=2)
        
        # Show the pattern of powers of i
        powers = VGroup(
            Text("i¹ = i", font_size=24, color=WHITE),
            Text("i² = -1", font_size=24, color=WHITE),
            Text("i³ = i² · i = -1 · i = -i", font_size=24, color=WHITE),
            Text("i⁴ = i² · i² = (-1) · (-1) = 1", font_size=24, color=WHITE),
            Text("i⁵ = i⁴ · i = 1 · i = i", font_size=24, color=YELLOW),
        )
        powers.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        powers.next_to(mult_title, DOWN, buff=0.5)
        
        pattern_explanation = Text("The pattern repeats every 4 powers!", font_size=22, color=GREEN)
        pattern_explanation.next_to(powers, DOWN, buff=0.5)
        
        for power in powers:
            self.play(Write(power), run_time=1.5)
            self.wait(1)
        
        self.play(Write(pattern_explanation), run_time=2)
        self.wait(3)
        
        # Show the cycle visually on the complex plane
        cycle_points = [
            plane.n2p(1),     # i⁰ = 1
            plane.n2p(1j),    # i¹ = i
            plane.n2p(-1),    # i² = -1
            plane.n2p(-1j),   # i³ = -i
            plane.n2p(1)      # i⁴ = 1
        ]
        
        cycle_arrows = []
        for i in range(len(cycle_points)-1):
            arrow = Arrow(cycle_points[i], cycle_points[i+1], color=GREEN, buff=0.1)
            cycle_arrows.append(arrow)
        
        for arrow in cycle_arrows:
            self.play(Create(arrow), run_time=1)
            self.wait(0.5)
        
        self.wait(2)
        
        # Phase 8: Complex Multiplication as Rotation (12 seconds)
        self.play(
            FadeOut(mult_title), FadeOut(powers), FadeOut(pattern_explanation),
            FadeOut(VGroup(*cycle_arrows)), run_time=2
        )
        
        rotation_title = Text("Multiplication as Rotation", font_size=28, color=PINK)
        rotation_title.next_to(plane_title, DOWN, buff=0.3)
        self.play(Write(rotation_title), run_time=2)
        
        # Show z1 again
        self.play(Create(vector1), Create(dot1), Write(label1), run_time=1.5)
        
        # Show z1 * i (90-degree rotation)
        z1_rotated = z1 * 1j
        dot1_rotated = Dot(plane.n2p(z1_rotated), color=PINK, radius=0.08)
        vector1_rotated = Arrow(plane.n2p(0), plane.n2p(z1_rotated), color=PINK, buff=0)
        label1_rotated = Text("3+2i × i = -2+3i", font_size=18, color=PINK).next_to(dot1_rotated, UL)
        
        rotation_explanation = Text("Multiplying by i rotates 90° counterclockwise", font_size=20, color=WHITE)
        rotation_explanation.next_to(rotation_title, DOWN, buff=0.5)
        self.play(Write(rotation_explanation), run_time=2)
        
        self.play(
            Rotate(vector1, PI/2, about_point=plane.n2p(0)),
            Transform(dot1, dot1_rotated),
            Transform(label1, label1_rotated),
            run_time=3
        )
        self.wait(2)
        
        # Show another rotation
        z1_rotated2 = z1_rotated * 1j
        dot1_rotated2 = Dot(plane.n2p(z1_rotated2), color=ORANGE, radius=0.08)
        label1_rotated2 = Text("× i again = -3-2i", font_size=18, color=ORANGE).next_to(dot1_rotated2, DL)
        
        self.play(
            Rotate(vector1, PI/2, about_point=plane.n2p(0)),
            Transform(dot1, dot1_rotated2),
            Transform(label1, label1_rotated2),
            run_time=3
        )
        self.wait(3)
        
        # Phase 9: Applications (10 seconds)
        self.play(
            FadeOut(rotation_title), FadeOut(rotation_explanation),
            FadeOut(vector1), FadeOut(dot1), FadeOut(label1), run_time=2
        )
        
        applications_title = Text("Applications of Complex Numbers", font_size=28, color=PURPLE)
        applications_title.next_to(plane_title, DOWN, buff=0.3)
        self.play(Write(applications_title), run_time=2)
        
        applications = VGroup(
            Text("• Electrical Engineering (AC circuits)", font_size=20, color=WHITE),
            Text("• Quantum Mechanics", font_size=20, color=WHITE),
            Text("• Signal Processing and Fourier Analysis", font_size=20, color=WHITE),
            Text("• Computer Graphics and Fractals", font_size=20, color=WHITE),
            Text("• Control Systems", font_size=20, color=WHITE)
        )
        applications.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        applications.next_to(applications_title, DOWN, buff=0.4)
        
        for app in applications:
            self.play(Write(app), run_time=1.2)
            self.wait(0.8)
        
        self.wait(3)
        
        # Phase 10: Final summary (8 seconds)
        self.play(FadeOut(applications_title), FadeOut(applications), run_time=1)
        
        summary_title = Text("Summary", font_size=32, color=YELLOW)
        summary_title.next_to(plane_title, DOWN, buff=0.5)
        
        summary_points = VGroup(
            Text("✓ Complex numbers: a + bi", font_size=22, color=WHITE),
            Text("✓ Extend real numbers to 2D plane", font_size=22, color=WHITE),
            Text("✓ Enable solutions to all polynomial equations", font_size=22, color=WHITE),
            Text("✓ Multiplication rotates and scales", font_size=22, color=WHITE)
        )
        summary_points.arrange(DOWN, aligned_edge=LEFT, buff=0.4)
        summary_points.next_to(summary_title, DOWN, buff=0.5)
        
        self.play(Write(summary_title), run_time=2)
        for point in summary_points:
            self.play(Write(point), run_time=1.5)
        
        self.wait(4)'''

def generate_diff_eq_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Create differential equation
        eq = Text(
            "\\frac{dy}{dx} + 2y = e^x"
        )
        
        # Solution steps
        step1 = Text(
            "y = e^{-2x}\\int e^x \\cdot e^{2x} dx"
        )
        step2 = Text(
            "y = e^{-2x}\\int e^{3x} dx"
        )
        step3 = Text(
            "y = e^{-2x} \\cdot \\frac{1}{3}e^{3x} + Ce^{-2x}"
        )
        step4 = Text(
            "y = \\frac{1}{3}e^x + Ce^{-2x}"
        )
        
        # Arrange equations
        VGroup(
            eq, step1, step2, step3, step4
        ).arrange(DOWN, buff=0.5)
        
        # Create graph
        axes = Axes(
            x_range=[-2, 2],
            y_range=[-2, 2],
            axis_config={"include_tip": True}
        )
        
        # Plot particular solution (C=0)
        graph = axes.plot(
            lambda x: (1/3)*np.exp(x),
            color=YELLOW
        )
        
        # Animations
        self.play(Write(eq))
        self.wait()
        self.play(Write(step1))
        self.wait()
        self.play(Write(step2))
        self.wait()
        self.play(Write(step3))
        self.wait()
        self.play(Write(step4))
        self.wait()
        
        # Show graph
        self.play(
            FadeOut(VGroup(eq, step1, step2, step3, step4))
        )
        self.play(Create(axes), Create(graph))
        self.wait()'''

def generate_trig_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Introduction phase (4 seconds)
        title = Text("Trigonometry: Unit Circle", font_size=44, color=YELLOW)
        subtitle = Text("Understanding Sine and Cosine", font_size=28, color="#00FFFF")
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=2)
        self.play(Write(subtitle), run_time=1.5)
        self.wait(2)
        
        # Clear and setup phase (3 seconds)
        self.play(FadeOut(title), FadeOut(subtitle))
        
        # Create coordinate system and unit circle
        axes = Axes(
            x_range=[-1.5, 1.5, 0.5], y_range=[-1.5, 1.5, 0.5],
            x_length=6, y_length=6,
            axis_config={"include_tip": True}
        )
        
        circle = Circle(radius=2, color=WHITE, stroke_width=3)
        
        # Add labels
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)
        circle_label = Text("Unit Circle (r = 1)", font_size=24, color=WHITE)
        circle_label.to_corner(UL)
        
        self.play(Create(axes), Write(x_label), Write(y_label), run_time=2)
        self.play(Create(circle), Write(circle_label), run_time=2)
        self.wait(1)
        
        # Explain the concept (4 seconds)
        concept_title = Text("Key Concept:", font_size=28, color=GREEN)
        concept_text = Text("Any point on unit circle: (cos θ, sin θ)", font_size=24, color=WHITE)
        concept_title.next_to(circle_label, DOWN, buff=0.5)
        concept_text.next_to(concept_title, DOWN, buff=0.3)
        
        self.play(Write(concept_title), run_time=1.5)
        self.play(Write(concept_text), run_time=2)
        self.wait(2)
        
        # Create angle tracker and moving elements (6 seconds)
        theta = ValueTracker(0)
        
        # Create radius line
        radius_line = always_redraw(
            lambda: Line(
                start=ORIGIN,
                end=circle.point_at_angle(theta.get_value()),
                color=YELLOW,
                stroke_width=4
            )
        )
        
        # Create moving point
        moving_dot = always_redraw(
            lambda: Dot(
                circle.point_at_angle(theta.get_value()),
                color=YELLOW,
                radius=0.08
            )
        )
        
        # Create projection lines
        x_projection = always_redraw(
            lambda: DashedLine(
                start=circle.point_at_angle(theta.get_value()),
                end=[circle.point_at_angle(theta.get_value())[0], 0, 0],
                color=BLUE,
                stroke_width=3
            )
        )
        
        y_projection = always_redraw(
            lambda: DashedLine(
                start=circle.point_at_angle(theta.get_value()),
                end=[0, circle.point_at_angle(theta.get_value())[1], 0],
                color=RED,
                stroke_width=3
            )
        )
        
        # Add angle arc
        angle_arc = always_redraw(
            lambda: Arc(
                start_angle=0,
                angle=theta.get_value(),
                radius=0.5,
                color=GREEN,
                stroke_width=3
            )
        )
        
        # Add value displays
        angle_text = always_redraw(
            lambda: Text(
                f"θ = {theta.get_value():.1f} rad",
                font_size=20,
                color=GREEN
            ).to_corner(UR)
        )
        
        cos_text = always_redraw(
            lambda: Text(
                f"cos θ = {np.cos(theta.get_value()):.2f}",
                font_size=20,
                color=BLUE
            ).next_to(angle_text, DOWN, buff=0.2)
        )
        
        sin_text = always_redraw(
            lambda: Text(
                f"sin θ = {np.sin(theta.get_value()):.2f}",
                font_size=20,
                color=RED
            ).next_to(cos_text, DOWN, buff=0.2)
        )
        
        # Add coordinate display
        coord_text = always_redraw(
            lambda: Text(
                f"Point: ({np.cos(theta.get_value()):.2f}, {np.sin(theta.get_value()):.2f})",
                font_size=18,
                color=YELLOW
            ).next_to(sin_text, DOWN, buff=0.2)
        )
        
        # Create all elements
        self.play(
            Create(radius_line), Create(moving_dot), Create(angle_arc),
            run_time=2
        )
        self.play(
            Create(x_projection), Create(y_projection),
            Write(angle_text), Write(cos_text), Write(sin_text), Write(coord_text),
            run_time=2
        )
        self.wait(2)
        
        # Animate through key angles (8 seconds)
        key_angles = [PI/6, PI/4, PI/3, PI/2, 2*PI/3, 3*PI/4, 5*PI/6, PI]
        angle_names = ["30°", "45°", "60°", "90°", "120°", "135°", "150°", "180°"]
        
        for i, (angle, name) in enumerate(zip(key_angles, angle_names)):
            # Create angle label
            angle_label = Text(f"{name}", font_size=20, color=ORANGE)
            angle_label.next_to(coord_text, DOWN, buff=0.2)
            
            self.play(
                theta.animate.set_value(angle),
                Write(angle_label),
                run_time=1
            )
            self.wait(0.5)
            self.play(FadeOut(angle_label), run_time=0.3)
        
        # Complete full rotation (4 seconds)
        completion_text = Text("Complete rotation: 0 to 2π", font_size=24, color=PURPLE)
        completion_text.move_to(DOWN * 2.5)
        self.play(Write(completion_text), run_time=1)
        
        self.play(
            theta.animate.set_value(2*PI),
            run_time=3,
            rate_func=linear
        )
        self.wait(1)
        
        # Show special triangles (5 seconds)
        self.play(FadeOut(completion_text))
        
        # Reset to 30-60-90 triangle
        self.play(theta.animate.set_value(PI/3), run_time=1)
        
        # Draw the triangle
        triangle_points = [
            ORIGIN,
            circle.point_at_angle(PI/3),
            [circle.point_at_angle(PI/3)[0], 0, 0]
        ]
        triangle = Polygon(*triangle_points, color=ORANGE, fill_opacity=0.3)
        
        triangle_label = Text("30-60-90 Triangle", font_size=20, color=ORANGE)
        triangle_label.move_to(DOWN * 2.5)
        
        self.play(Create(triangle), Write(triangle_label), run_time=2)
        self.wait(2)
        
        # Show exact values
        exact_values = Text("sin(60°) = √3/2, cos(60°) = 1/2", font_size=18, color=WHITE)
        exact_values.next_to(triangle_label, DOWN, buff=0.3)
        self.play(Write(exact_values), run_time=2)
        self.wait(2)
        
        # Final summary (3 seconds)
        summary = Text("Unit circle: Foundation of trigonometry!", font_size=28, color=GREEN)
        summary.move_to(DOWN * 3.5)
        self.play(Write(summary), run_time=2)
        self.wait(3)'''

def generate_quadratic_code():
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Create coordinate system
        axes = Axes(
            x_range=[-4, 4],
            y_range=[-2, 8],
            axis_config={"include_tip": True}
        )
        
        # Add custom labels
        x_label = Text("x").next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y").next_to(axes.y_axis.get_end(), UP)
        
        # Create quadratic function
        def func(x):
            return x**2
            
        graph = axes.plot(
            func,
            color=BLUE,
            x_range=[-3, 3]
        )
        
        # Create labels and equation
        equation = Text("f(x) = x²").to_corner(UL)
        
        # Create dot and value tracker
        x = ValueTracker(-3)
        dot = always_redraw(
            lambda: Dot(
                axes.c2p(
                    x.get_value(),
                    func(x.get_value())
                ),
                color=YELLOW
            )
        )
        
        # Create lines to show x and y values
        v_line = always_redraw(
            lambda: axes.get_vertical_line(
                axes.input_to_graph_point(
                    x.get_value(),
                    graph
                ),
                color=RED
            )
        )
        h_line = always_redraw(
            lambda: axes.get_horizontal_line(
                axes.input_to_graph_point(
                    x.get_value(),
                    graph
                ),
                color=GREEN
            )
        )
        
        # Add everything to scene
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(graph))
        self.play(Write(equation))
        self.play(Create(dot), Create(v_line), Create(h_line))
        
        # Animate x value
        self.play(
            x.animate.set_value(3),
            run_time=6,
            rate_func=there_and_back
        )
        self.wait()'''

def generate_3d_surface_code():
    return '''from manim import *

class MainScene(ThreeDScene):
    def construct(self):
        # Configure the scene
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        
        # Create axes
        axes = ThreeDAxes()
        
        # Create surface
        def func(x, y):
            return np.sin(x) * np.cos(y)
            
        surface = Surface(
            lambda u, v: axes.c2p(u, v, func(u, v)),
            u_range=[-3, 3],
            v_range=[-3, 3],
            resolution=32,
            checkerboard_colors=[BLUE_D, BLUE_E]
        )
        
        # Add custom labels
        x_label = Text("x").next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y").next_to(axes.y_axis.get_end(), UP)
        z_label = Text("z").next_to(axes.z_axis.get_end(), OUT)
        
        # Create animations
        self.begin_ambient_camera_rotation(rate=0.2)
        self.play(Create(axes), Write(x_label), Write(y_label), Write(z_label))
        self.play(Create(surface))
        self.wait(2)
        self.stop_ambient_camera_rotation()
        self.wait()'''

def generate_sphere_code():
    return '''from manim import *

class MainScene(ThreeDScene):
    def construct(self):
        # Configure the scene
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)
        
        # Create axes
        axes = ThreeDAxes()
        
        # Create sphere
        sphere = Surface(
            lambda u, v: np.array([
                np.cos(u) * np.cos(v),
                np.cos(u) * np.sin(v),
                np.sin(u)
            ]),
            u_range=[-PI/2, PI/2],
            v_range=[0, TAU],
            checkerboard_colors=[BLUE_D, BLUE_E]
        )
        
        # Add custom labels
        x_label = Text("x").next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y").next_to(axes.y_axis.get_end(), UP)
        z_label = Text("z").next_to(axes.z_axis.get_end(), OUT)
        
        # Create animations
        self.begin_ambient_camera_rotation(rate=0.2)
        self.play(Create(axes), Write(x_label), Write(y_label), Write(z_label))
        self.play(Create(sphere))
        self.wait(2)
        self.stop_ambient_camera_rotation()
        self.wait()'''

def generate_manim_code(concept):
    """Generate completely original Manim code using Google Gemini with comprehensive documentation reference."""
    try:
        # ALWAYS use AI generation for original, comprehensive content
        print(f"Generating original AI script for: {concept}")
        
        # Generate comprehensive prompt with full documentation
        prompt = generate_manim_prompt(concept)
        print(f"DEBUG: Generated prompt length: {len(prompt)} characters")
        
        # Try up to 3 times for successful generation
        for attempt in range(3):
            print(f"DEBUG: Generation attempt {attempt + 1}/3")
            
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash-lite',  # Use 1.5-flash which doesn't have thinking mode
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4 + (attempt * 0.1),
                    max_output_tokens=8192,  # Increase token limit
                )
            )
        
            # Check if response is valid
            if not response:
                print(f"DEBUG: Attempt {attempt + 1} - No response object from Gemini API")
                if attempt == 2:  # Last attempt
                    raise Exception("No response object from Gemini API after 3 attempts")
                continue
            
            # Check for MAX_TOKENS finish reason
            if (hasattr(response, 'candidates') and response.candidates and 
                hasattr(response.candidates[0], 'finish_reason') and 
                str(response.candidates[0].finish_reason) == 'MAX_TOKENS'):
                print(f"DEBUG: Attempt {attempt + 1} - Hit MAX_TOKENS, retrying with simpler prompt")
                if attempt < 2:  # Not the last attempt
                    # Simplify the prompt for the next attempt
                    prompt = f"Create a simple Manim animation to explain: {concept}\n\nGenerate complete Python code with class MainScene(Scene): and construct method. Keep it under 6000 tokens."
                    continue
                else:
                    raise Exception("Hit MAX_TOKENS on all attempts")
            
            if not hasattr(response, 'text') or not response.text:
                print(f"DEBUG: Attempt {attempt + 1} - Empty response text")
                print(f"DEBUG: Response object: {response}")
                print(f"DEBUG: Response attributes: {dir(response)}")
                if hasattr(response, 'candidates') and response.candidates:
                    print(f"DEBUG: Candidates: {response.candidates}")
                    if response.candidates[0].content:
                        print(f"DEBUG: Content parts: {response.candidates[0].content.parts}")
                if attempt == 2:  # Last attempt
                    raise Exception("Empty response text from Gemini API after 3 attempts")
                continue
            
            # Success - we have a valid response
            print(f"DEBUG: Received response length: {len(response.text)} characters")
            break
        
        # Extract the generated code from the response
        generated_code = response.text
        
        # Clean up the response to extract just the Python code
        if "```python" in generated_code:
            start = generated_code.find("```python") + 9
            end = generated_code.find("```", start)
            if end != -1:
                generated_code = generated_code[start:end].strip()
            else:
                generated_code = generated_code[start:].strip()
        elif "```" in generated_code:
            start = generated_code.find("```") + 3
            end = generated_code.find("```", start)
            if end != -1:
                generated_code = generated_code[start:end].strip()
        
        # Validate that the code starts with proper imports
        if not generated_code.startswith("from manim import"):
            generated_code = "from manim import *\n\n" + generated_code
        
        # Clean up problematic color references
        generated_code = fix_color_references(generated_code)
        
        # Add syntax validation before returning
        try:
            compile(generated_code, '<string>', 'exec')
            print("Syntax validation passed")
        except SyntaxError as syntax_err:
            print(f"Syntax error detected: {syntax_err}")
            print(f"Error at line {syntax_err.lineno}: {syntax_err.text}")
            
            # Try to fix common syntax errors
            if "was never closed" in str(syntax_err):
                print("Attempting to fix unclosed parentheses/brackets...")
                lines = generated_code.split('\n')
                if syntax_err.lineno and syntax_err.lineno <= len(lines):
                    problem_line_idx = syntax_err.lineno - 1
                    problem_line = lines[problem_line_idx]
                    
                    # Check for missing closing parentheses
                    open_parens = problem_line.count('(')
                    close_parens = problem_line.count(')')
                    
                    if open_parens > close_parens:
                        # Add missing closing parentheses
                        missing_parens = open_parens - close_parens
                        lines[problem_line_idx] = problem_line + ')' * missing_parens
                        generated_code = '\n'.join(lines)
                        print(f"Added {missing_parens} closing parenthesis/parentheses")
                        
                        # Re-validate
                        try:
                            compile(generated_code, '<string>', 'exec')
                            print("Syntax validation passed after fix")
                        except SyntaxError as new_err:
                            print(f"Syntax fix failed: {new_err}")
                            return generate_error_fallback(concept, str(syntax_err))
                    else:
                        print("Could not determine fix for syntax error")
                        return generate_error_fallback(concept, str(syntax_err))
            else:
                return generate_error_fallback(concept, str(syntax_err))
        
        # Validate the generated code has substantial content
        if len(generated_code) < 1000:  # If too short, regenerate with more emphasis
            print("Generated code seems too short, requesting more comprehensive version...")
            enhanced_prompt = prompt + "\n\nIMPORTANT: The previous attempt was too short. Generate a MUCH longer, more comprehensive script with extensive explanations, multiple examples, and detailed step-by-step breakdowns. Minimum 60-90 seconds of content with substantial educational value."
            
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.5,
                    max_output_tokens=8192,  # Increased for enhanced generation
                )
            )
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini API on retry")
            
            # Re-extract and clean the enhanced code
            generated_code = response.text
            if "```python" in generated_code:
                start = generated_code.find("```python") + 9
                end = generated_code.find("```", start)
                if end != -1:
                    generated_code = generated_code[start:end].strip()
                else:
                    generated_code = generated_code[start:].strip()
            elif "```" in generated_code:
                start = generated_code.find("```") + 3
                end = generated_code.find("```", start)
                if end != -1:
                    generated_code = generated_code[start:end].strip()
            
            if not generated_code.startswith("from manim import"):
                generated_code = "from manim import *\n\n" + generated_code
            
            generated_code = fix_color_references(generated_code)
        
        print(f"Successfully generated original script with {len(generated_code)} characters")
        return generated_code
        
    except Exception as e:
        print(f"AI generation failed with error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Create a more informative error script that shows what went wrong
        return f'''from manim import *

class MainScene(Scene):
    def construct(self):
        # AI Generation failed for concept: {concept}
        error_title = Text("AI Generation Error", font_size=36, color="#FF6B6B")
        error_detail = Text(f"Error: {str(e)[:50]}...", font_size=20, color="#FFAA00")
        error_msg = Text("Please check logs and try again", font_size=18, color="#FFFFFF")
        
        error_detail.next_to(error_title, DOWN, buff=0.5)
        error_msg.next_to(error_detail, DOWN, buff=0.5)
        
        self.play(Write(error_title), run_time=2)
        self.play(Write(error_detail), run_time=2)
        self.play(Write(error_msg), run_time=2)
        self.wait(5)'''
        
    except Exception as e:
        app.logger.error(f"Error generating Manim code with Gemini: {str(e)}")
        # Fallback to template-based generation
        try:
            return select_template(concept.lower())
        except Exception as template_error:
            app.logger.error(f"Template fallback also failed: {str(template_error)}")
            return generate_simple_basic_code()

def fix_color_references(code):
    """Fix problematic color references and escape sequences in generated code"""
    # Replace problematic colors with safe ones
    color_replacements = {
        'CYAN': '"#00FFFF"',
        'ORANGE': '"#FFA500"',
        'PURPLE': '"#800080"',
        'PINK': '"#FFC0CB"',
        'LIGHT_GREEN': '"#90EE90"',
        'DARK_BLUE': '"#00008B"',
        'LIGHT_BLUE': '"#ADD8E6"'
    }
    
    for old_color, new_color in color_replacements.items():
        code = code.replace(f'color={old_color}', f'color={new_color}')
        code = code.replace(f'color={old_color})', f'color={new_color})')
    
    # Fix common LaTeX escape sequences in MathTex strings
    import re
    
    # Find MathTex strings and fix escape sequences within them
    def fix_mathtex_escapes(match):
        content = match.group(1)
        # Fix common LaTeX escape sequences
        content = content.replace('\\s', '\\\\s')
        content = content.replace('\\p', '\\\\p')
        content = content.replace('\\f', '\\\\f')
        return f'MathTex("{content}"'
    
    # Apply fixes to MathTex strings
    code = re.sub(r'MathTex\("([^"]+)"', fix_mathtex_escapes, code)
    
    return code

def generate_simple_integral_code():
    """Generate a simple, safe integral visualization"""
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Title (3 seconds)
        title = Text("Integration: Area Under Curve", font_size=36, color=YELLOW)
        self.play(Write(title), run_time=2)
        self.wait(2)
        self.play(FadeOut(title), run_time=1)
        
        # Create axes (2 seconds)
        axes = Axes(
            x_range=[0, 4, 1], y_range=[0, 3, 1],
            x_length=8, y_length=6,
            axis_config={"include_tip": True}
        )
        self.play(Create(axes), run_time=2)
        
        # Add function (3 seconds)
        def func(x):
            return 0.5 * x + 0.5
            
        graph = axes.plot(func, color=BLUE, x_range=[0.5, 3.5])
        func_label = Text("f(x) = 0.5x + 0.5", font_size=24, color=BLUE)
        func_label.to_corner(UL)
        
        self.play(Create(graph), run_time=2)
        self.play(Write(func_label), run_time=1)
        
        # Show area (4 seconds)
        area = axes.get_area(
            graph, x_range=[1, 3], color=GREEN, opacity=0.6
        )
        area_label = Text("Area = ∫₁³ f(x) dx", font_size=24, color=GREEN)
        area_label.next_to(func_label, DOWN, buff=0.3)
        
        self.play(FadeIn(area), run_time=2)
        self.play(Write(area_label), run_time=2)
        self.wait(2)
        
        # Show calculation (4 seconds)
        calc1 = Text("= ∫₁³ (0.5x + 0.5) dx", font_size=20, color=WHITE)
        calc2 = Text("= [0.25x² + 0.5x]₁³", font_size=20, color=WHITE)
        calc3 = Text("= (2.25 + 1.5) - (0.25 + 0.5)", font_size=20, color=WHITE)
        calc4 = Text("= 3.75 - 0.75 = 3", font_size=20, color=YELLOW)
        
        calcs = VGroup(calc1, calc2, calc3, calc4)
        calcs.arrange(DOWN, buff=0.2)
        calcs.move_to(DOWN * 1.5)
        
        for calc in calcs:
            self.play(Write(calc), run_time=1)
            self.wait(0.5)
        
        self.wait(3)'''

def generate_simple_basic_code():
    """Generate a simple, safe basic visualization"""
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Title (3 seconds)
        title = Text("Mathematical Visualization", font_size=40, color=YELLOW)
        self.play(Write(title), run_time=2)
        self.wait(2)
        self.play(FadeOut(title), run_time=1)
        
        # Create axes (2 seconds)
        axes = Axes(
            x_range=[-3, 3, 1], y_range=[-2, 2, 1],
            x_length=8, y_length=6,
            axis_config={"include_tip": True}
        )
        self.play(Create(axes), run_time=2)
        
        # Add sine function (4 seconds)
        sin_graph = axes.plot(lambda x: np.sin(x), color=BLUE, x_range=[-3, 3])
        sin_label = Text("f(x) = sin(x)", font_size=24, color=BLUE)
        sin_label.to_corner(UL)
        
        self.play(Create(sin_graph), run_time=3)
        self.play(Write(sin_label), run_time=1)
        self.wait(1)
        
        # Add cosine function (4 seconds)
        cos_graph = axes.plot(lambda x: np.cos(x), color=RED, x_range=[-3, 3])
        cos_label = Text("g(x) = cos(x)", font_size=24, color=RED)
        cos_label.next_to(sin_label, DOWN, buff=0.2)
        
        self.play(Create(cos_graph), run_time=3)
        self.play(Write(cos_label), run_time=1)
        self.wait(1)
        
        # Show properties (5 seconds)
        prop1 = Text("• Both functions are periodic", font_size=18, color=WHITE)
        prop2 = Text("• Period = 2π", font_size=18, color=WHITE)
        prop3 = Text("• Range: [-1, 1]", font_size=18, color=WHITE)
        prop4 = Text("• cos(x) = sin(x + π/2)", font_size=18, color=WHITE)
        
        props = VGroup(prop1, prop2, prop3, prop4)
        props.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        props.move_to(DOWN * 2)
        
        for prop in props:
            self.play(Write(prop), run_time=1)
            self.wait(0.2)
        
        self.wait(3)'''

def generate_basic_visualization_code():
    """Generate code for enhanced basic visualization."""
    return '''from manim import *

class MainScene(Scene):
    def construct(self):
        # Introduction phase (4 seconds)
        title = Text("Mathematical Function Visualization", font_size=40, color=YELLOW)
        subtitle = Text("Exploring Trigonometric Functions", font_size=28, color="#00FFFF")
        subtitle.next_to(title, DOWN, buff=0.5)
        
        self.play(Write(title), run_time=2)
        self.play(Write(subtitle), run_time=1.5)
        self.wait(2)
        
        # Clear and setup phase (3 seconds)
        self.play(FadeOut(title), FadeOut(subtitle))
        
        # Create coordinate system
        axes = Axes(
            x_range=[-2*PI, 2*PI, PI/2], y_range=[-2, 2, 1],
            x_length=12, y_length=6,
            axis_config={"include_tip": True}
        )
        
        # Add detailed labels
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)
        
        # Add pi markings
        pi_labels = VGroup()
        for i in [-2, -1, 0, 1, 2]:
            if i == 0:
                label = Text("0", font_size=16)
            elif i == 1:
                label = Text("π", font_size=16)
            elif i == -1:
                label = Text("-π", font_size=16)
            else:
                label = Text(f"{i}π", font_size=16)
            label.next_to(axes.c2p(i*PI, 0), DOWN, buff=0.2)
            pi_labels.add(label)
        
        self.play(Create(axes), Write(x_label), Write(y_label), run_time=2)
        self.play(Write(pi_labels), run_time=1.5)
        self.wait(1)
        
        # Introduce sine function (5 seconds)
        sin_title = Text("Sine Function", font_size=32, color=BLUE)
        sin_title.to_corner(UL)
        sin_equation = Text("f(x) = sin(x)", font_size=28, color=BLUE)
        sin_equation.next_to(sin_title, DOWN, buff=0.3)
        
        self.play(Write(sin_title), Write(sin_equation), run_time=2)
        
        # Draw sine graph progressively
        sin_graph = axes.plot(lambda x: np.sin(x), color=BLUE, x_range=[-2*PI, 2*PI])
        self.play(Create(sin_graph), run_time=3)
        self.wait(2)
        
        # Show key properties of sine (4 seconds)
        properties_title = Text("Properties:", font_size=24, color=WHITE)
        prop1 = Text("• Period: 2π", font_size=20, color=WHITE)
        prop2 = Text("• Range: [-1, 1]", font_size=20, color=WHITE)
        prop3 = Text("• Amplitude: 1", font_size=20, color=WHITE)
        
        properties = VGroup(properties_title, prop1, prop2, prop3)
        properties.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        properties.next_to(sin_equation, DOWN, buff=0.5)
        
        for prop in properties:
            self.play(Write(prop), run_time=0.8)
        self.wait(2)
        
        # Introduce cosine function (5 seconds)
        cos_title = Text("Cosine Function", font_size=28, color=RED)
        cos_equation = Text("g(x) = cos(x)", font_size=24, color=RED)
        cos_title.move_to(UP * 2 + RIGHT * 4)
        cos_equation.next_to(cos_title, DOWN, buff=0.2)
        
        self.play(Write(cos_title), Write(cos_equation), run_time=2)
        
        # Draw cosine graph
        cos_graph = axes.plot(lambda x: np.cos(x), color=RED, x_range=[-2*PI, 2*PI])
        self.play(Create(cos_graph), run_time=3)
        self.wait(1)
        
        # Show relationship between sine and cosine (6 seconds)
        relationship_text = Text("cos(x) = sin(x + π/2)", font_size=24, color=PURPLE)
        relationship_text.next_to(cos_equation, DOWN, buff=0.5)
        self.play(Write(relationship_text), run_time=2)
        
        # Create moving dot to show the relationship
        moving_dot_sin = Dot(color=BLUE, radius=0.08)
        moving_dot_cos = Dot(color=RED, radius=0.08)
        
        # Add value trackers
        angle_tracker = ValueTracker(-2*PI)
        
        def update_sin_dot(mob):
            x = angle_tracker.get_value()
            y = np.sin(x)
            mob.move_to(axes.c2p(x, y))
            
        def update_cos_dot(mob):
            x = angle_tracker.get_value()
            y = np.cos(x)
            mob.move_to(axes.c2p(x, y))
        
        moving_dot_sin.add_updater(update_sin_dot)
        moving_dot_cos.add_updater(update_cos_dot)
        
        # Show current values
        value_text = Text("", font_size=20)
        def update_values(mob):
            x = angle_tracker.get_value()
            sin_val = np.sin(x)
            cos_val = np.cos(x)
            mob.become(Text(f"x = {x:.1f}, sin(x) = {sin_val:.2f}, cos(x) = {cos_val:.2f}", 
                          font_size=20, color=WHITE))
            mob.to_corner(DR)
        
        value_text.add_updater(update_values)
        
        self.add(moving_dot_sin, moving_dot_cos, value_text)
        
        self.play(
            angle_tracker.animate.set_value(2*PI),
            run_time=4,
            rate_func=linear
        )
        self.wait(1)
        
        # Show unit circle connection (5 seconds)
        self.play(FadeOut(properties), FadeOut(relationship_text))
        
        # Create unit circle
        circle = Circle(radius=1.5, color=GREEN).move_to(LEFT * 4 + UP * 1)
        circle_title = Text("Unit Circle", font_size=24, color=GREEN)
        circle_title.next_to(circle, UP, buff=0.3)
        
        self.play(Create(circle), Write(circle_title), run_time=2)
        
        # Show connection
        connection_text = Text("Functions come from unit circle!", font_size=20, color=GREEN)
        connection_text.next_to(circle, DOWN, buff=0.3)
        self.play(Write(connection_text), run_time=1.5)
        self.wait(2)
        
        # Final summary (4 seconds)
        summary_title = Text("Summary:", font_size=28, color=YELLOW)
        summary1 = Text("• Sine and cosine are periodic functions", font_size=18, color=WHITE)
        summary2 = Text("• They oscillate between -1 and 1", font_size=18, color=WHITE)
        summary3 = Text("• Phase difference of π/2 radians", font_size=18, color=WHITE)
        summary4 = Text("• Fundamental in mathematics and physics", font_size=18, color=WHITE)
        
        summary_group = VGroup(summary_title, summary1, summary2, summary3, summary4)
        summary_group.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        summary_group.move_to(DOWN * 2)
        
        for item in summary_group:
            self.play(Write(item), run_time=0.8)
        
        self.wait(3)'''

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/chat')
def chat():
    """Serve the chat page."""
    return render_template('chat.html')

@app.route('/chat', methods=['POST'])
def chat_api():
    """Handle chat API requests."""
    try:
        data = request.json
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'No message provided'}), 400
            
        message = sanitize_input(message)
        
        # Generate response using Gemini AI
        response = generate_chat_response(message)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        logger.error(f'Error in chat API: {str(e)}')
        return jsonify({
            'error': 'Failed to generate response',
            'details': str(e)
        }), 500

def generate_chat_response(message):
    """Generate chat response using Gemini AI."""
    try:
        # Create a comprehensive prompt for mathematical assistance
        prompt = f"""You are MathsGPT, an expert AI mathematics tutor and assistant. You specialize in:

1. Explaining mathematical concepts clearly and step-by-step
2. Solving mathematical problems with detailed workings
3. Providing educational insights and real-world applications
4. Helping with calculus, algebra, geometry, trigonometry, linear algebra, differential equations, complex numbers, and more
5. Breaking down complex topics into understandable parts

User message: {message}

Please provide a helpful, educational, and engaging response. Use clear explanations, examples where appropriate, and maintain a friendly, encouraging tone. If the question involves calculations, show your work step by step. If it's about concepts, provide intuitive explanations along with the formal definitions.

Format your response in a conversational way that would work well in a chat interface. You can use basic formatting like **bold** for emphasis and *italics* for mathematical terms. Use bullet points or numbered lists when helpful.

Keep your response comprehensive but not overwhelming - aim for 2-4 paragraphs unless the topic requires more detail."""

        response = genai_client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )
        
        if not response or not response.text:
            return "I apologize, but I'm having trouble generating a response right now. Please try asking your question again."
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f'Error generating chat response: {str(e)}')
        return "I apologize, but I encountered an error while processing your request. Please try again with a different question."

@app.route('/generate', methods=['POST'])
def generate():
    start_time = time.time()
    user_ip = request.remote_addr
    
    try:
        concept = request.json.get('concept', '')
        if not concept:
            return jsonify({'error': 'No concept provided'}), 400
            
        concept = sanitize_input(concept)
        
        # Send start notification
        notify_generation_start(concept, user_ip)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=6))
        filename = f'scene_{timestamp}_{random_str}'
        
        # Create temporary directory for this generation
        temp_dir = os.path.join(app.config['TEMP_DIR'], filename)
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Get Manim code using Gemini AI - NO TEMPLATES FALLBACK
            print(f"DEBUG: Starting AI generation for concept: '{concept}'")
            manim_code = generate_manim_code(concept)
            print(f"DEBUG: Generated code length: {len(manim_code)} characters")
            print(f"DEBUG: Code preview: {manim_code[:200]}...")
        except Exception as code_gen_error:
            logger.error(f'Code generation error: {str(code_gen_error)}')
            print(f"DEBUG: Code generation failed with error: {code_gen_error}")
            # Send error notification
            notify_generation_error(concept, f"Code generation failed: {str(code_gen_error)}", user_ip)
            # Return error instead of basic visualization
            return jsonify({'error': f'AI code generation failed: {str(code_gen_error)}'}), 500
            
        if not manim_code:
            notify_generation_error(concept, "Failed to generate code", user_ip)
            return jsonify({'error': 'Failed to generate code'}), 500
            
        # Write code to temporary file
        code_file = os.path.join(temp_dir, 'scene.py')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(manim_code)
        
        # Create media directory
        media_dir = os.path.join(temp_dir, 'media')
        os.makedirs(media_dir, exist_ok=True)
        
        # Run manim command with error handling
        output_file = os.path.join(app.static_folder, 'videos', f'{filename}.mp4')
        command = [
            'py', '-m', 'manim',
            'render',
            '-qm',  # medium quality
            '--format', 'mp4',
            '--media_dir', media_dir,
            code_file,
            'MainScene'
        ]
        
        logger.info(f'Processing concept: {concept}')
        logger.info(f'Running Manim command: {" ".join(command)}')
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=temp_dir,
                timeout=10000  # 167 minute timeoutut=10000  # 167 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout if result.stdout else 'Unknown error during animation generation'
                logger.error(f'Manim command failed with return code {result.returncode}')
                logger.error(f'Manim stderr: {result.stderr}')
                logger.error(f'Manim stdout: {result.stdout}')
                logger.error(f'Generated code that failed:\n{manim_code}')
                
                # Send error notification
                notify_generation_error(concept, f"Manim rendering failed: {error_msg}", user_ip)
                
                return jsonify({
                    'error': 'Failed to generate animation',
                    'details': error_msg,
                    'return_code': result.returncode
                }), 500
            
            # Look for the video file in multiple possible locations
            possible_paths = [
                os.path.join(media_dir, 'videos', 'scene', '1080p60', 'MainScene.mp4'),
                os.path.join(media_dir, 'videos', 'scene', '720p30', 'MainScene.mp4'),
                os.path.join(media_dir, 'videos', 'MainScene.mp4'),
                os.path.join(temp_dir, 'MainScene.mp4')
            ]
            
            video_found = False
            file_size = 0
            for source_path in possible_paths:
                if os.path.exists(source_path):
                    shutil.move(source_path, output_file)
                    video_found = True
                    # Get file size in MB
                    file_size = os.path.getsize(output_file) / (1024 * 1024)
                    break
            
            if not video_found:
                error_msg = f'Video not found in any of these locations: {possible_paths}'
                logger.error(error_msg)
                notify_generation_error(concept, error_msg, user_ip)
                return jsonify({'error': 'Generated video file not found'}), 500
            
            # Calculate generation time
            duration = time.time() - start_time
            
            # Send success notification
            notify_generation_success(concept, duration, file_size, user_ip)
            
            # Return success response
            return jsonify({
                'success': True,
                'video_url': url_for('static', filename=f'videos/{filename}.mp4'),
                'code': manim_code
            })
            
        except subprocess.TimeoutExpired:
            error_msg = 'Animation generation timed out. The animation took too long to generate.'
            notify_generation_error(concept, error_msg, user_ip)
            return jsonify({
                'error': 'Animation generation timed out',
                'details': 'The animation took too long to generate. Please try a simpler concept.'
            }), 500
                
        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        logger.error(f'Error generating animation: {str(e)}')
        notify_generation_error(concept if 'concept' in locals() else 'Unknown', str(e), user_ip)
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/telegram-status')
def telegram_status():
    """Check Telegram bot configuration status"""
    return jsonify({
        'configured': telegram_notifier.is_configured(),
        'bot_token_exists': bool(telegram_notifier.bot_token),
        'chat_id_exists': bool(telegram_notifier.chat_id),
        'bot_instance_exists': bool(telegram_notifier.bot)
    })

@app.route('/test-telegram', methods=['POST'])
def test_telegram():
    """Test Telegram notification"""
    try:
        if not telegram_notifier.is_configured():
            return jsonify({
                'error': 'Telegram bot not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.'
            }), 400
        
        test_message = "🧪 Test notification from Manim Video Generator!\n\nIf you received this, notifications are working correctly! 🎉"
        success = notify_system_alert('info', test_message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Test notification sent successfully!'
            })
        else:
            return jsonify({
                'error': 'Failed to send test notification. Check bot token and chat ID.'
            }), 500
            
    except Exception as e:
        logger.error(f'Error testing Telegram: {str(e)}')
        return jsonify({
            'error': 'Error testing Telegram notification',
            'details': str(e)
        }), 500

@app.route('/update-docs', methods=['POST'])
def update_docs():
    """Update Manim documentation reference"""
    try:
        import subprocess
        script_path = os.path.join(app.root_path, 'scrape_manim_docs.py')
        
        if os.path.exists(script_path):
            result = subprocess.run(['py', script_path], 
                                  capture_output=True, text=True, cwd=app.root_path)
            
            if result.returncode == 0:
                # Reload the documentation
                global MANIM_DOCS
                MANIM_DOCS = load_manim_docs()
                
                return jsonify({
                    'success': True,
                    'message': 'Documentation updated successfully!',
                    'size': len(MANIM_DOCS)
                })
            else:
                return jsonify({
                    'error': 'Failed to update documentation',
                    'details': result.stderr
                }), 500
        else:
            return jsonify({
                'error': 'Documentation scraper not found'
            }), 500
            
    except Exception as e:
        return jsonify({
            'error': 'Error updating documentation',
            'details': str(e)
        }), 500

@app.route('/static/videos/<path:filename>')
def serve_video(filename):
    """Serve video files from static/videos directory."""
    try:
        return send_from_directory(
            os.path.join(app.root_path, 'static', 'videos'),
            filename,
            mimetype='video/mp4'
        )
    except Exception as e:
        app.logger.error(f"Error serving video {filename}: {str(e)}")
        return jsonify({'error': 'Video not found'}), 404


if __name__ == '__main__':
    # Send startup notification
    startup_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notify_system_alert('info', f'Manim Video Generator started successfully at {startup_time}')
    
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)