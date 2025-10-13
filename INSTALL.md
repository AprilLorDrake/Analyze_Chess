# Installation Guide for Analyze Chess

## Method 1: Direct Installation from GitHub

### Prerequisites
- Python 3.8 or higher
- Git

### Steps
1. Clone the repository:
   `ash
   git clone https://github.com/AprilLorDrake/Analyze_Chess.git
   cd Analyze_Chess
   `

2. Create virtual environment:
   `ash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   `

3. Install dependencies:
   `ash
   pip install -r requirements.txt
   `

4. Run the application:
   `ash
   python app.py
   `

5. Open browser to: http://localhost:5000

## Method 2: Python Package Installation (Coming Soon)

Once published to GitHub Packages:

`ash
pip install --index-url https://pypi.org/simple/ analyze-chess
analyze-chess
`

## Method 3: Docker Container

### Prerequisites
- Docker installed

### Steps
1. Pull and run the container:
   `ash
   docker run -p 5000:5000 ghcr.io/aprillordrake/analyze_chess:latest
   `

2. Open browser to: http://localhost:5000

## Method 4: One-Click Deploy

### Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/AprilLorDrake/Analyze_Chess)

### Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/AprilLorDrake/Analyze_Chess)

## System Requirements
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.8 or higher
- **Memory**: 512MB RAM minimum, 1GB recommended
- **Storage**: 100MB free space
- **Network**: Internet connection for Stockfish updates

## Troubleshooting

### Common Issues
1. **Port 5000 already in use**:
   - Change port in pp.py: pp.run(host='0.0.0.0', port=8000)

2. **Stockfish not found**:
   - The app will auto-download Stockfish on first run
   - Or manually place Stockfish binary in in/ directory

3. **Python dependencies error**:
   - Ensure you're using Python 3.8+
   - Try: pip install --upgrade pip setuptools wheel

### Support
-  Report issues: [GitHub Issues](https://github.com/AprilLorDrake/Analyze_Chess/issues)
-  Documentation: [README.md](https://github.com/AprilLorDrake/Analyze_Chess/blob/master/README.md)
