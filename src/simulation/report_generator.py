"""
Report Generator for Streaming JSON Parser Benchmarks

Analyzes benchmark results and generates comprehensive performance reports
with rankings, the best algorithm identification, and detailed analysis.
"""
import argparse
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PerformanceCategory:
    """Represents a performance category for analysis."""
    metric_key: str
    display_name: str
    lower_is_better: bool = True


class ResultsLoader:
    """Handles loading of benchmark results from files."""
    
    def load_results(self, csv_path: Path) -> pd.DataFrame:
        """Load benchmark results from CSV file."""
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} benchmark results from {csv_path}")
            return df
        except Exception as e:
            logger.error(f"Error loading results from {csv_path}: {e}")
            raise


class FileFinder:
    """Finds the most recent benchmark result files."""
    
    def __init__(self, results_dir: Path):
        self._results_dir = results_dir
    
    def find_latest_results(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Find the most recent benchmark result files."""
        csv_files = list(self._results_dir.glob("benchmark_results_*.csv"))
        json_files = list(self._results_dir.glob("benchmark_results_*.json"))
        
        if not csv_files:
            logger.warning("No CSV result files found")
            return None, None
        
        # Sort by modification time and get the latest
        latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
        latest_json = None
        
        if json_files:
            latest_json = max(json_files, key=lambda f: f.stat().st_mtime)
        
        return latest_csv, latest_json


class PerformanceCategoryManager:
    """Manages performance categories for analysis."""
    
    def __init__(self):
        self._categories = [
            PerformanceCategory('serialize_time_ms', 'Serialization Speed', True),
            PerformanceCategory('deserialize_time_ms', 'Deserialization Speed', True),
            PerformanceCategory('throughput_mbps', 'Throughput (MB/s)', False),
            PerformanceCategory('memory_peak_bytes', 'Memory Efficiency', True),
            PerformanceCategory('cpu_time_seconds', 'CPU Efficiency', True),
            PerformanceCategory('dataset_size', 'Data Size', True),
            PerformanceCategory('total_ser_deser_time_ms', 'Total Processing Time', True)
        ]
    
    def get_categories(self) -> List[PerformanceCategory]:
        """Get all performance categories."""
        return self._categories
    
    def get_category_by_key(self, key: str) -> Optional[PerformanceCategory]:
        """Get category by metric key."""
        return next((cat for cat in self._categories if cat.metric_key == key), None)


class StatisticsCalculator:
    """Calculates statistics for performance analysis."""
    
    def calculate_algorithm_statistics(self, df: pd.DataFrame, 
                                     algorithm_col: str) -> Dict[str, Dict[str, Any]]:
        """Calculate statistics per algorithm for all metrics."""
        statistics = {}
        category_manager = PerformanceCategoryManager()
        
        for category in category_manager.get_categories():
            if category.metric_key not in df.columns:
                continue
            
            # Calculate statistics per algorithm
            stats = df.groupby(algorithm_col)[category.metric_key].agg([
                'mean', 'median', 'std', 'min', 'max', 'count'
            ]).round(4)
            
            statistics[category.metric_key] = stats.to_dict('index')
        
        return statistics


class RankingGenerator:
    """Generates rankings for different performance categories."""
    
    def generate_rankings(self, statistics: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate rankings for each performance category."""
        rankings = {}
        category_manager = PerformanceCategoryManager()
        
        for category in category_manager.get_categories():
            if category.metric_key not in statistics:
                continue
            
            stats_df = pd.DataFrame(statistics[category.metric_key]).T
            if stats_df.empty:
                continue
            
            # Sort based on whether lower or higher is better
            ascending = category.lower_is_better
            ranked = stats_df.sort_values('mean', ascending=ascending)
            rankings[category.metric_key] = ranked.index.tolist()
        
        return rankings


class BestAlgorithmFinder:
    """Finds the best algorithm for each performance category."""
    
    def find_best_algorithms(self, rankings: Dict[str, List[str]]) -> Dict[str, str]:
        """Find the best algorithm for each category."""
        best_algorithms = {}
        
        for metric, ranked_algorithms in rankings.items():
            if ranked_algorithms:
                best_algorithms[metric] = ranked_algorithms[0]
        
        return best_algorithms


class PerformanceAnalyzer:
    """Main performance analyzer that orchestrates the analysis."""
    
    def __init__(self):
        self._stats_calculator = StatisticsCalculator()
        self._ranking_generator = RankingGenerator()
        self._best_finder = BestAlgorithmFinder()
    
    def analyze_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance across all categories."""
        analysis = {
            'summary': {},
            'rankings': {},
            'best_algorithms': {},
            'statistics': {}
        }
        
        # Get unique algorithms
        algorithm_col = self._get_algorithm_column(df)
        algorithms = df[algorithm_col].unique()
        
        analysis['summary']['total_algorithms'] = len(algorithms)
        analysis['summary']['total_tests'] = len(df)
        
        # Calculate statistics
        analysis['statistics'] = self._stats_calculator.calculate_algorithm_statistics(df, algorithm_col)
        
        # Generate rankings
        analysis['rankings'] = self._ranking_generator.generate_rankings(analysis['statistics'])
        
        # Find best algorithms
        analysis['best_algorithms'] = self._best_finder.find_best_algorithms(analysis['rankings'])
        
        return analysis
    
    def _get_algorithm_column(self, df: pd.DataFrame) -> str:
        """Get the algorithm column name."""
        return 'algorithm_name' if 'algorithm_name' in df.columns else 'algorithm'


class ValueFormatter:
    """Formats values for display in reports."""
    
    def format_value(self, value: float, metric: str) -> str:
        """Format value based on metric type."""
        if 'time_ms' in metric:
            return f"{value:.2f}ms"
        elif 'time_seconds' in metric:
            return f"{value:.3f}s"
        elif 'throughput' in metric:
            return f"{value:.1f}MB/s"
        elif 'memory' in metric or 'bytes' in metric:
            return f"{value/1024/1024:.1f}MB"
        elif 'dataset_size' in metric:
            return f"{value:.0f} records"
        else:
            return f"{value:.2f}"


class EmojiRankingGenerator:
    """Generates emoji-formatted rankings."""
    
    def __init__(self):
        self._formatter = ValueFormatter()
        self._category_manager = PerformanceCategoryManager()
    
    def generate_emoji_rankings(self, analysis: Dict[str, Any]) -> str:
        """Generate emoji-formatted rankings for each category."""
        rankings_text = []
        
        for category in self._category_manager.get_categories():
            if category.metric_key not in analysis['rankings']:
                continue
            
            rankings_text.append(f"\n🏆 {category.display_name.upper()}:")
            
            # Get the top 3 algorithms for this metric
            top_algorithms = analysis['rankings'][category.metric_key][:3]
            
            for i, algo in enumerate(top_algorithms):
                if (category.metric_key in analysis['statistics'] and 
                    algo in analysis['statistics'][category.metric_key]):
                    
                    value = analysis['statistics'][category.metric_key][algo]['mean']
                    formatted_value = self._formatter.format_value(value, category.metric_key)
                    
                    emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉"
                    rankings_text.append(f"  {emoji} {i+1}. {algo}: {formatted_value}")
        
        return "\n".join(rankings_text)


class DetailedAnalysisGenerator:
    """Generates detailed performance analysis."""
    
    def __init__(self):
        self._emoji_generator = EmojiRankingGenerator()
        self._category_manager = PerformanceCategoryManager()
        self._formatter = ValueFormatter()
    
    def generate_detailed_analysis(self, analysis: Dict[str, Any], df: pd.DataFrame) -> str:
        """Generate detailed performance analysis."""
        report_lines = [
            "# STREAMING JSON PARSER BENCHMARK ANALYSIS",
            "=" * 50,
            f"📊 **Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"🔬 **Total Algorithms Tested:** {analysis['summary']['total_algorithms']}",
            f"📈 **Total Benchmark Runs:** {analysis['summary']['total_tests']}",
            "\n## 🏆 CHAMPION ALGORITHMS BY CATEGORY",
            "-" * 40
        ]
        
        # Best Algorithm Summary
        self._add_best_algorithms_summary(report_lines, analysis)
        
        # Detailed Rankings
        report_lines.append(self._emoji_generator.generate_emoji_rankings(analysis))
        
        # Performance Insights
        self._add_performance_insights(report_lines, analysis)
        
        # Algorithm comparison matrix
        self._add_algorithm_comparison(report_lines, df)
        
        return "\n".join(report_lines)
    
    def _add_best_algorithms_summary(self, report_lines: List[str], analysis: Dict[str, Any]) -> None:
        """Add best algorithms summary to report."""
        for category in self._category_manager.get_categories():
            if category.metric_key in analysis['best_algorithms']:
                best_algo = analysis['best_algorithms'][category.metric_key]
                
                if (category.metric_key in analysis['statistics'] and 
                    best_algo in analysis['statistics'][category.metric_key]):
                    
                    value = analysis['statistics'][category.metric_key][best_algo]['mean']
                    formatted_value = self._formatter.format_value(value, category.metric_key)
                    report_lines.append(f"🏃 **{category.display_name}:** {best_algo} ({formatted_value})")
    
    def _add_performance_insights(self, report_lines: List[str], analysis: Dict[str, Any]) -> None:
        """Add performance insights to report."""
        report_lines.extend([
            "\n## 📊 PERFORMANCE INSIGHTS",
            "-" * 30
        ])
        
        # Find overall best performers
        serialization_best = analysis['best_algorithms'].get('serialize_time_ms', 'N/A')
        throughput_best = analysis['best_algorithms'].get('throughput_mbps', 'N/A')
        memory_best = analysis['best_algorithms'].get('memory_peak_bytes', 'N/A')
        
        report_lines.extend([
            f"⚡ **Speed Champion:** {serialization_best}",
            f"🚀 **Throughput Leader:** {throughput_best}",
            f"💾 **Memory Efficient:** {memory_best}"
        ])
    
    def _add_algorithm_comparison(self, report_lines: List[str], df: pd.DataFrame) -> None:
        """Add algorithm comparison matrix to report."""
        report_lines.extend([
            "\n## 📋 ALGORITHM COMPARISON MATRIX",
            "-" * 35
        ])
        
        algorithm_col = 'algorithm_name' if 'algorithm_name' in df.columns else 'algorithm'
        algorithms = df[algorithm_col].unique()
        
        for algo in algorithms:
            algo_data = df[df[algorithm_col] == algo]
            if len(algo_data) > 0:
                self._add_algorithm_stats(report_lines, algo, algo_data)
    
    def _add_algorithm_stats(self, report_lines: List[str], algo: str, algo_data: pd.DataFrame) -> None:
        """Add statistics for a single algorithm."""
        avg_ser_time = algo_data['serialize_time_ms'].mean() if 'serialize_time_ms' in algo_data.columns else 0
        avg_deser_time = algo_data['deserialize_time_ms'].mean() if 'deserialize_time_ms' in algo_data.columns else 0
        avg_throughput = algo_data['throughput_mbps'].mean() if 'throughput_mbps' in algo_data.columns else 0
        
        report_lines.extend([
            f"\n**{algo}:**",
            f"  • Serialization: {avg_ser_time:.2f}ms",
            f"  • Deserialization: {avg_deser_time:.2f}ms",
            f"  • Throughput: {avg_throughput:.1f}MB/s"
        ])


class CsvExporter:
    """Exports analysis summary to CSV format."""
    
    def __init__(self):
        self._category_manager = PerformanceCategoryManager()
    
    def export_csv_summary(self, analysis: Dict[str, Any], output_path: Path) -> None:
        """Export analysis summary to CSV format."""
        summary_data = []
        
        for category in self._category_manager.get_categories():
            if category.metric_key in analysis['rankings']:
                self._add_category_data(summary_data, category, analysis)
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(output_path, index=False)
        logger.info(f"CSV summary exported to {output_path}")
    
    def _add_category_data(self, summary_data: List[Dict], category: PerformanceCategory, 
                          analysis: Dict[str, Any]) -> None:
        """Add data for a single category."""
        for rank, algo in enumerate(analysis['rankings'][category.metric_key], 1):
            if (category.metric_key in analysis['statistics'] and 
                algo in analysis['statistics'][category.metric_key]):
                
                stats = analysis['statistics'][category.metric_key][algo]
                summary_data.append({
                    'Category': category.display_name,
                    'Rank': rank,
                    'Algorithm': algo,
                    'Mean_Value': stats['mean'],
                    'Median_Value': stats['median'],
                    'Std_Dev': stats['std'],
                    'Min_Value': stats['min'],
                    'Max_Value': stats['max'],
                    'Test_Count': stats['count']
                })


class JsonExporter:
    """Exports complete analysis to JSON format."""
    
    def export_json_report(self, analysis: Dict[str, Any], output_path: Path) -> None:
        """Export complete analysis to JSON format."""
        # Convert numpy types to native Python types for JSON serialization
        json_analysis = self._convert_numpy_types(analysis)
        
        # Add metadata
        json_analysis['metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'generator_version': '1.0.0',
            'categories_analyzed': [cat.metric_key for cat in PerformanceCategoryManager().get_categories()]
        }
        
        with open(output_path, 'w') as f:
            json.dump(json_analysis, f, indent=2)
        logger.info(f"JSON report exported to {output_path}")
    
    def _convert_numpy_types(self, obj: Any) -> Any:
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        return obj


class ReportGenerator:
    """Generates comprehensive analysis reports from benchmark results."""
    
    def __init__(self, results_dir: str = ".", output_dir: str = "."):
        """
        Initialize the report generator.
        
        Args:
            results_dir: Directory containing benchmark result files
            output_dir: Directory to save generated reports
        """
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self._results_loader = ResultsLoader()
        self._file_finder = FileFinder(self.results_dir)
        self._performance_analyzer = PerformanceAnalyzer()
        self._detailed_generator = DetailedAnalysisGenerator()
        self._csv_exporter = CsvExporter()
        self._json_exporter = JsonExporter()
    
    def find_latest_results(self) -> Tuple[Optional[Path], Optional[Path]]:
        """Find the most recent benchmark result files."""
        return self._file_finder.find_latest_results()
    
    def analyze_performance(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze performance across all categories."""
        return self._performance_analyzer.analyze_performance(df)
    
    def generate_detailed_analysis(self, analysis: Dict[str, Any], df: pd.DataFrame) -> str:
        """Generate detailed performance analysis."""
        return self._detailed_generator.generate_detailed_analysis(analysis, df)
    
    def export_csv_summary(self, analysis: Dict[str, Any], output_path: Path) -> None:
        """Export analysis summary to CSV format."""
        self._csv_exporter.export_csv_summary(analysis, output_path)
    
    def export_json_report(self, analysis: Dict[str, Any], output_path: Path) -> None:
        """Export complete analysis to JSON format."""
        self._json_exporter.export_json_report(analysis, output_path)
    
    def generate_report(self, results_file: Optional[str] = None) -> str:
        """
        Generate a comprehensive benchmark analysis report.
        
        Args:
            results_file: Specific results file to analyze (optional)
            
        Returns:
            Path to generated report file
        """
        # Find or use the specified results file
        csv_path = self._get_results_file(results_file)
        
        # Load and analyze results
        df = self._results_loader.load_results(csv_path)
        analysis = self.analyze_performance(df)
        
        # Generate reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Text report
        report_content = self.generate_detailed_analysis(analysis, df)
        report_path = self.output_dir / f"benchmark_analysis_{timestamp}.md"
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        # CSV summary
        csv_summary_path = self.output_dir / f"benchmark_summary_{timestamp}.csv"
        self.export_csv_summary(analysis, csv_summary_path)
        
        # JSON report
        json_report_path = self.output_dir / f"benchmark_analysis_{timestamp}.json"
        self.export_json_report(analysis, json_report_path)
        
        logger.info("Reports generated:")
        logger.info(f"  - Analysis: {report_path}")
        logger.info(f"  - CSV Summary: {csv_summary_path}")
        logger.info(f"  - JSON Report: {json_report_path}")
        
        return str(report_path)
    
    def _get_results_file(self, results_file: Optional[str]) -> Path:
        """Get the results file to analyze."""
        if results_file:
            csv_path = Path(results_file)
            if not csv_path.exists():
                raise FileNotFoundError(f"Results file not found: {results_file}")
            return csv_path
        else:
            csv_path, _ = self.find_latest_results()
            if not csv_path:
                raise FileNotFoundError("No benchmark results found")
            return csv_path


class ArgumentParser:
    """Handles command line argument parsing."""
    
    @staticmethod
    def parse_args() -> 'argparse.Namespace':
        """Parse command line arguments."""
        import argparse
        
        parser = argparse.ArgumentParser(description="Generate streaming JSON parser benchmark reports")
        parser.add_argument("--results-dir", default=".", help="Directory containing benchmark results")
        parser.add_argument("--output-dir", default=".", help="Directory to save generated reports")
        parser.add_argument("--results-file", help="Specific results file to analyze")
        parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
        
        return parser.parse_args()


def main():
    """Command line interface for report generation."""
    arg_parser = ArgumentParser()
    args = arg_parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        generator = ReportGenerator(args.results_dir, args.output_dir)
        report_path = generator.generate_report(args.results_file)
        print(f"✅ Report generated successfully: {report_path}")
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())