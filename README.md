# Manim Video Generator 🎬

A web-based tool for generating mathematical animations using Manim, Flask, and AI. Create beautiful mathematical visualizations with simple text prompts and chat with an AI assistant about mathematics.

[![manim video generator](https://img.youtube.com/vi/rIltjjzxsGQ/0.jpg)](https://www.youtube.com/watch?v=rIltjjzxsGQ)

## 🌟 Features

- Generate mathematical animations from text descriptions
- Interactive chat interface with AI mathematics tutor
- Modern, responsive web interface
- Real-time code preview with syntax highlighting
- Support for various mathematical concepts
- Easy-to-use example prompts
- Docker support for easy deployment
- Video generation directly in chat conversations

## 🚀 Quick Start

1. Clone the repository:
```bash
git clone https://github.com/KNIGHTABDO/manim-video-generator.git
cd manim-video-generator
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Google AI API key
```

4. Run the application:
```bash
python app.py
```

5. Visit `http://localhost:5001` in your browser

## 🐳 Docker Setup

1. Build the Docker image:
```bash
docker build -t manim-generator .
```

2. Run the container:
```bash
docker run -p 5001:5001 -v $(pwd)/media:/app/media manim-generator
```

## 💬 Chat Feature

The application now includes an intelligent chat interface where you can:
- Ask mathematical questions and get detailed explanations
- Request video generation directly in the chat
- Get step-by-step solutions to mathematical problems
- Discuss complex mathematical concepts with the AI tutor

## 📝 Usage Notes

- Ensure your mathematical concepts are clearly described
- Complex animations may take longer to generate
- Use the chat feature for mathematical discussions and video requests
- Supported topics include:
  - Basic geometry and algebra
  - Calculus concepts
  - 3D visualizations
  - Matrix operations
  - Complex numbers
  - Differential equations
  - Trigonometry
  - Linear algebra

## 🎥 Showcase

Here are some examples of complex mathematical animations generated using our tool:

### Complex Analysis Visualization
<img src="static/gifs/complex_analysis.gif" width="800" alt="Complex Number Transformations">

*This animation demonstrates complex number transformations, showing how functions map points in the complex plane. Watch as the visualization reveals the geometric interpretation of complex operations.*

### 3D Calculus Concepts
<img src="static/gifs/3d_calculus.gif" width="800" alt="3D Surface Integration">

*A sophisticated 3D visualization showing multivariable calculus concepts. The animation illustrates surface integrals and vector fields in three-dimensional space, making abstract concepts tangible.*

### Differential Equations
<img src="static/gifs/differential_equations.gif" width="800" alt="Differential Equations">

*This animation brings differential equations to life by visualizing solution curves and phase spaces. Watch how the system evolves over time, revealing the underlying mathematical patterns.*

### Linear Algebra Transformations
<img src="static/gifs/ComplexNumbersAnimation_ManimCE_v0.17.3.gif" width="800" alt="Linear Transformations">

*Experience linear transformations in action! This visualization demonstrates how matrices transform space, showing concepts like eigenvectors, rotations, and scaling in an intuitive way.*

These examples showcase the power of our tool in creating complex mathematical visualizations. Each animation is generated from a simple text description, demonstrating the capability to:
- Render sophisticated 3D scenes with proper lighting and perspective
- Create smooth transitions between mathematical concepts
- Visualize abstract mathematical relationships
- Handle multiple mathematical objects with precise timing
- Generate publication-quality animations for educational purposes

## 🔧 Requirements

- Python 3.10+
- FFmpeg
- Cairo
- LaTeX (for mathematical typesetting)
- Google AI API key

## 🤝 Credits

- Created by [KNIGHT](https://github.com/KNIGHTABDO)
- Powered by [Manim Community](https://www.manim.community/)
- Special thanks to:
  - [3Blue1Brown](https://www.3blue1brown.com/) for creating Manim
  - The Manim Community for their excellent documentation and support
  - Google AI for providing the Gemini API

## 📄 License

This project is open source and available under the MIT License.

## 🔗 Links

- [Manim Documentation](https://docs.manim.community/)
- [3Blue1Brown's Manim](https://3b1b.github.io/manim/)
- [Google AI API](https://ai.google.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🤔 Common Issues & Solutions

1. **LaTeX Errors**
   - Ensure you have a complete LaTeX distribution installed
   - Check for syntax errors in mathematical expressions

2. **Rendering Issues**
   - Verify FFmpeg installation
   - Check Cairo dependencies
   - Ensure sufficient system resources

3. **API Rate Limits**
   - Monitor Google AI API usage
   - Implement appropriate rate limiting
   - Consider upgrading API plan for high traffic

4. **Chat Feature Issues**
   - Ensure Google AI API key is properly configured
   - Check network connectivity
   - Verify API key permissions

## 🎯 Future Roadmap

- [x] Interactive chat interface with AI tutor
- [x] Video generation in chat conversations
- [ ] User authentication system
- [ ] Save and share animations
- [ ] Custom animation templates
- [ ] Batch processing
- [ ] Advanced customization options
- [ ] API endpoint for programmatic access
- [ ] Enhanced chat features with mathematical notation support

## 💡 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

If you encounter any issues or have questions, please:
1. Check the [Common Issues](#-common-issues--solutions) section
2. Search existing GitHub issues
3. Create a new issue if needed
4. Contact [KNIGHT](https://github.com/KNIGHTABDO) for direct support

## 🚀 Deployment

This application is ready for deployment on various platforms:

### Render Deployment
1. Connect your GitHub repository to Render
2. Set environment variables (GOOGLE_API_KEY, etc.)
3. Deploy using the included Dockerfile and render.yaml

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run the application
python app.py
```

---

Made with ❤️ by [KNIGHT](https://github.com/KNIGHTABDO) using Manim, Flask, and Google AI