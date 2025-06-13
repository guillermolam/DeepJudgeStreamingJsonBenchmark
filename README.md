# Streaming JSON Parser Benchmark Suite

A comprehensive benchmarking framework for evaluating and comparing 12 different streaming JSON parser implementations
across multiple performance metrics including serialization speed, deserialization speed, throughput, memory usage, CPU
efficiency, and network performance.

## 🏗️ Project Structure

```
streaming_json_benchmark/
├── 📦 serializers/                    # Parser implementations package
│   ├── __init__.py                    # Package exports and imports
│   ├── json_parser.py                 # Standard JSON library parser
│   ├── ultrajson_parser.py            # Ultra-fast JSON parser (ujson)
│   ├── bson_parser.py                 # Binary JSON (BSON) parser
│   ├── cbor_parser.py                 # Concise Binary Object Representation
│   ├── msgpack_parser.py              # MessagePack binary serialization
│   ├── pickle_binary_mono_parser.py   # Python Pickle (single-threaded)
│   ├── pickle_binary_multi_parser.py  # Python Pickle (multi-threaded)
│   ├── marshall_parser.py             # Python Marshall serialization
│   ├── protobuf_parser.py             # Protocol Buffers parser
│   ├── flatbuffers_parser.py          # Google FlatBuffers parser
│   ├── parquet_parser.py              # Apache Parquet columnar format
│   └── reactivex_parser.py            # ReactiveX streaming parser
├── 🔬 simulation/                     # Benchmarking and analysis tools
│   ├── __init__.py                    # Package exports and imports
│   ├── benchmark_runner.py           # Main benchmarking orchestrator
│   ├── data_gen.py                    # Test data generation utilities
│   ├── net_sim.py                     # Network condition simulation
│   ├── algo_metadata.py               # Algorithm metadata and configuration
│   ├── utils.py                       # Common utilities and helpers
│   └── report_generator.py            # Performance analysis and reporting
├── 🧪 tests/                          # Test suite package
│   ├── __init__.py                    # Test package initialization
│   ├── test_parsers.py                # Unit tests for all parsers
│   └── test_working_parsers.py        # Integration tests for working parsers
├── 📋 Configuration Files
│   ├── pyproject.toml                 # Modern Python packaging configuration
│   ├── requirements.txt               # Python dependencies list
│   ├── setup.cfg                      # Tool configuration (pytest, flake8, mypy)
│   └── .gitignore                     # Git ignore patterns
├── 📖 Documentation
│   └── README.md                      # This comprehensive guide
└── 🚀 Entry Points
    └── main.py                        # Main application entry point
```

## 🚀 Quick Start

### Installation

1. **Clone or download the project:**
   ```bash
   cd /home/ubuntu/streaming_json_benchmark
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install as editable package (optional):**
   ```bash
   pip install -e .
   ```

### Running Benchmarks

#### Option 1: Full Benchmark Suite (Recommended)

```bash
# Run complete benchmark with analysis report
python main.py

# Save results to specific directory
python main.py --output-dir ./results

# Enable verbose logging
python main.py --verbose
```

#### Option 2: Generate Report Only

```bash
# Generate report from existing results
python main.py --report-only

# Analyze specific results file
python main.py --report-only --results-file benchmark_results_20250612_155326.csv
```

#### Option 3: Direct Module Execution

```bash
# Run benchmark runner directly
python -m simulation.benchmark_runner

# Generate report directly
python -m simulation.report_generator --results-dir . --output-dir ./reports
```

## 💻 Platform-Specific Instructions

### 🐧 Linux/macOS (Bash/Zsh)

```bash
# Navigate to project directory
cd /home/ubuntu/streaming_json_benchmark

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run benchmark suite
python main.py --output-dir ./results --verbose
```

### 🪟 Windows (PowerShell)

```powershell
# Navigate to project directory
cd C:\path\to\streaming_json_benchmark

# Create virtual environment (recommended)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run benchmark suite
python main.py --output-dir .\results --verbose
```

### 🔧 PyCharm IDE

1. **Open Project:**
    - File → Open → Select `streaming_json_benchmark` directory

2. **Configure Python Interpreter:**
    - File → Settings → Project → Python Interpreter
    - Add new interpreter or use existing Python 3.8+

3. **Install Dependencies:**
    - Open Terminal in PyCharm
    - Run: `pip install -r requirements.txt`

4. **Run Configuration:**
    - Right-click `main.py` → Run 'main'
    - Or create run configuration:
        - Script path: `/path/to/main.py`
        - Parameters: `--output-dir ./results --verbose`
        - Working directory: `/path/to/streaming_json_benchmark`

5. **Run Tests:**
    - Right-click `tests/` directory → Run 'pytest in tests'

## 📊 Output Configuration

### Changing Output Directory

The benchmark suite allows you to specify where results and logs are saved:

```bash
# Save to custom directory
python main.py --output-dir /path/to/custom/results

# Save to relative directory
python main.py --output-dir ./benchmark_results

# Default (current directory)
python main.py
```

### Generated Files

When you run the benchmark suite, the following files are generated:

```
output_directory/
├── 📊 benchmark_results_YYYYMMDD_HHMMSS.csv    # Raw benchmark data
├── 📊 benchmark_results_YYYYMMDD_HHMMSS.json   # Detailed results with metadata
├── 📈 benchmark_analysis_YYYYMMDD_HHMMSS.md    # Human-readable analysis report
├── 📋 benchmark_summary_YYYYMMDD_HHMMSS.csv    # Performance rankings summary
├── 📊 benchmark_analysis_YYYYMMDD_HHMMSS.json  # Machine-readable analysis
└── 📝 benchmark.log                            # Execution logs
```

## 🏆 Performance Categories

The benchmark suite evaluates parsers across these key metrics:

- **🏃 Serialization Speed:** Time to convert objects to serialized format
- **📖 Deserialization Speed:** Time to parse serialized data back to objects
- **🚀 Throughput:** Data processing rate (MB/s)
- **💾 Memory Efficiency:** RAM usage during operations
- **⚡ CPU Efficiency:** Processor utilization percentage
- **📦 Data Compression:** Serialized data size efficiency
- **🌐 Network Performance:** Latency and bandwidth simulation

## 📈 Sample Report Output

```
🏆 CHAMPION ALGORITHMS BY CATEGORY
----------------------------------------
🏃 Serialization Speed: Pickle Binary Mono (0.06ms)
📖 Deserialization Speed: Ultra JSON (0.04ms)  
🚀 Throughput: MessagePack (245.3MB/s)
💾 Memory Efficiency: CBOR (12.4MB)
⚡ CPU Efficiency: JSON Standard (15.2%)
📦 Data Compression: Protocol Buffers (2.1KB)
🌐 Network Performance: FlatBuffers (8.3ms)

🏆 SERIALIZATION SPEED:
  🥇 1. Pickle Binary Mono: 0.06ms
  🥈 2. Ultra JSON: 0.09ms
  🥉 3. MessagePack: 0.12ms

🏆 THROUGHPUT (MB/S):
  🥇 1. MessagePack: 245.3MB/s
  🥈 2. CBOR: 198.7MB/s
  🥉 3. Ultra JSON: 187.2MB/s
```

## 🧪 Testing

Run the test suite to verify all components:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=serializers --cov=simulation

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m benchmark     # Benchmark tests only

# Run tests with verbose output
pytest -v

# Run tests for specific module
pytest tests/test_parsers.py
```

## 🔧 Development

### Code Quality Tools

The project includes configuration for various development tools:

```bash
# Code formatting
black .

# Import sorting
isort .

# Linting
flake8

# Type checking
mypy serializers/ simulation/

# Pre-commit hooks (optional)
pre-commit install
pre-commit run --all-files
```

### Adding New Parsers

1. Create new parser in `serializers/` following the existing pattern
2. Add import to `serializers/__init__.py`
3. Update `simulation/algo_metadata.py` with parser configuration
4. Add tests in `tests/`
5. Update documentation

## 📋 Dependencies

### Core Requirements

- **pandas** (≥1.5.0) - Data analysis and manipulation
- **numpy** (≥1.21.0) - Numerical computing
- **ujson** (≥5.0.0) - Ultra-fast JSON encoder/decoder
- **pymongo** (≥4.0.0) - BSON support
- **cbor2** (≥5.4.0) - CBOR encoding/decoding
- **msgpack** (≥1.0.0) - MessagePack serialization
- **protobuf** (≥4.0.0) - Protocol Buffers
- **flatbuffers** (≥2.0.0) - FlatBuffers serialization
- **pyarrow** (≥10.0.0) - Parquet format support
- **reactivex** (≥4.0.0) - Reactive programming
- **psutil** (≥5.8.0) - System monitoring
- **matplotlib** (≥3.5.0) - Plotting and visualization
- **seaborn** (≥0.11.0) - Statistical visualization
- **tqdm** (≥4.60.0) - Progress bars
- **colorama** (≥0.4.4) - Colored terminal output
- **tabulate** (≥0.9.0) - Table formatting

### Development Dependencies (Optional)

- **pytest** (≥7.0.0) - Testing framework
- **black** (≥22.0.0) - Code formatter
- **flake8** (≥5.0.0) - Linting
- **mypy** (≥1.0.0) - Type checking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Run code quality checks: `black . && flake8 && mypy`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Import Errors:**
   ```bash
   # Ensure you're in the project root directory
   cd /home/ubuntu/streaming_json_benchmark
   
   # Install missing dependencies
   pip install -r requirements.txt
   ```

2. **Permission Errors:**
   ```bash
   # Make main.py executable (Linux/macOS)
   chmod +x main.py
   ```

3. **Module Not Found:**
   ```bash
   # Add project to Python path
   export PYTHONPATH="${PYTHONPATH}:/home/ubuntu/streaming_json_benchmark"
   ```

4. **Memory Issues:**
   ```bash
   # Reduce test data size in data_gen.py
   # Or run with smaller datasets
   python main.py --output-dir ./results
   ```

### Getting Help

- Check the logs in `benchmark.log` for detailed error information
- Run with `--verbose` flag for more detailed output
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Verify Python version: `python --version` (requires Python 3.8+)

## 🎯 Performance Tips

- Run benchmarks on a dedicated machine for consistent results
- Close unnecessary applications during benchmarking
- Use SSD storage for better I/O performance
- Ensure adequate RAM (8GB+ recommended)
- Run multiple iterations for statistical significance

---

**Happy Benchmarking! 🚀**
