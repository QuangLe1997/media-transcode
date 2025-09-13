#!/usr/bin/env python3
"""
WebP Test Suite - Batch testing different configurations
Script để test nhiều config khác nhau và so sánh kết quả
"""

import os
import json
import time
from pathlib import Path
# from video_to_webp_converter import VideoToWebPConverter  # Module not found
from typing import List, Dict, Any

class WebPTestSuite:
    def __init__(self, input_video: str, output_dir: str = "webp_tests"):
        self.input_video = input_video
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        # self.converter = VideoToWebPConverter()  # Module not found
        self.results = []

    def run_preset_tests(self) -> List[Dict[str, Any]]:
        """Test các preset khác nhau"""
        print("🎯 Testing Different Presets...")

        presets = [
            {"name": "high_quality", "quality": 90, "method": 6, "fps": 15},
            {"name": "medium_quality", "quality": 75, "method": 4, "fps": 15},
            {"name": "low_quality", "quality": 60, "method": 2, "fps": 12},
            {"name": "ultra_low", "quality": 40, "method": 1, "fps": 10},
            {"name": "lossless", "lossless": True, "method": 6, "fps": 15},
            {"name": "photo_preset", "quality": 80, "preset": "photo", "method": 4, "fps": 15},
            {"name": "drawing_preset", "quality": 85, "preset": "drawing", "method": 5, "fps": 15}
        ]

        results = []
        for preset in presets:
            name = preset.pop("name")
            output_path = self.output_dir / f"preset_{name}.webp"

            print(f"\n📋 Testing: {name}")
            # result = self.converter.convert(  # Module not found
            #     input_path=self.input_video,
            #     output_path=str(output_path),
            #     verbose=False,
            #     **preset
            # )
            result = {"success": False, "error": "VideoToWebPConverter not available"}

            result["test_name"] = name
            result["config"] = preset
            results.append(result)

            if result.get('success'):
                file_size = result.get('file_size_mb', 0)
                time_sec = result.get('conversion_time_seconds', 0)
                print(f"✅ {name}: {file_size:.2f}MB, {time_sec:.1f}s")
            else:
                print(f"❌ {name}: FAILED")

        return results

    def run_size_comparison_tests(self) -> List[Dict[str, Any]]:
        """Test các kích thước khác nhau"""
        print("\n📏 Testing Different Sizes...")

        sizes = [
            {"name": "original", "width": None, "height": None},
            {"name": "720p", "width": 1280, "height": 720},
            {"name": "480p", "width": 854, "height": 480},
            {"name": "360p", "width": 640, "height": 360},
            {"name": "240p", "width": 426, "height": 240},
            {"name": "square_500", "width": 500, "height": 500},
            {"name": "portrait_360x640", "width": 360, "height": 640}
        ]

        results = []
        base_config = {"quality": 75, "method": 4, "fps": 15}

        for size_config in sizes:
            name = size_config.pop("name")
            output_path = self.output_dir / f"size_{name}.webp"

            config = {**base_config, **size_config}

            print(f"\n📐 Testing: {name}")
            # result = self.converter.convert(  # Module not found
            #     input_path=self.input_video,
            #     output_path=str(output_path),
            #     verbose=False,
            #     **config
            # )
            result = {"success": False, "error": "VideoToWebPConverter not available"}

            result["test_name"] = name
            result["config"] = config
            results.append(result)

            if result.get('success'):
                dimensions = f"{result.get('width', 0)}×{result.get('height', 0)}"
                print(f"✅ {name}: {dimensions}, {result.get('file_size_mb', 0):.2f}MB")
            else:
                print(f"❌ {name}: FAILED")

        return results

    def run_fps_comparison_tests(self) -> List[Dict[str, Any]]:
        """Test các FPS khác nhau"""
        print("\n🎞️ Testing Different Frame Rates...")

        fps_values = [30, 24, 15, 12, 10, 8, 5]
        results = []
        base_config = {"quality": 75, "method": 4, "width": 640, "height": 480}

        for fps in fps_values:
            name = f"fps_{fps}"
            output_path = self.output_dir / f"{name}.webp"

            config = {**base_config, "fps": fps}

            print(f"\n⏱️ Testing: {fps} FPS")
            # result = self.converter.convert(  # Module not found
            #     input_path=self.input_video,
            #     output_path=str(output_path),
            #     verbose=False,
            #     **config
            # )
            result = {"success": False, "error": "VideoToWebPConverter not available"}

            result["test_name"] = name
            result["config"] = config
            results.append(result)

            if result.get('success'):
                file_size = result.get('file_size_mb', 0)
                frames = result.get('frames', 0)
                print(f"✅ {fps} FPS: {file_size:.2f}MB, {frames} frames")
            else:
                print(f"❌ {fps} FPS: FAILED")

        return results

    def run_quality_comparison_tests(self) -> List[Dict[str, Any]]:
        """Test các mức quality khác nhau"""
        print("\n🎨 Testing Different Quality Settings...")

        qualities = [100, 90, 80, 75, 70, 60, 50, 40, 30, 20]
        results = []
        base_config = {"method": 4, "fps": 15, "width": 640, "height": 480}

        for quality in qualities:
            name = f"quality_{quality}"
            output_path = self.output_dir / f"{name}.webp"

            config = {**base_config, "quality": quality}

            print(f"\n🎯 Testing: Quality {quality}")
            # result = self.converter.convert(  # Module not found
            #     input_path=self.input_video,
            #     output_path=str(output_path),
            #     verbose=False,
            #     **config
            # )
            result = {"success": False, "error": "VideoToWebPConverter not available"}

            result["test_name"] = name
            result["config"] = config
            results.append(result)

            if result.get('success'):
                print(f"✅ Q{quality}: {result.get('file_size_mb', 0):.2f}MB")
            else:
                print(f"❌ Q{quality}: FAILED")

        return results

    def run_method_comparison_tests(self) -> List[Dict[str, Any]]:
        """Test các compression method khác nhau"""
        print("\n⚙️ Testing Different Compression Methods...")

        methods = [0, 1, 2, 3, 4, 5, 6]
        results = []
        base_config = {"quality": 75, "fps": 15, "width": 640, "height": 480}

        for method in methods:
            name = f"method_{method}"
            output_path = self.output_dir / f"{name}.webp"

            config = {**base_config, "method": method}

            print(f"\n🔧 Testing: Method {method}")
            # result = self.converter.convert(  # Module not found
            #     input_path=self.input_video,
            #     output_path=str(output_path),
            #     verbose=False,
            #     **config
            # )
            result = {"success": False, "error": "VideoToWebPConverter not available"}

            result["test_name"] = name
            result["config"] = config
            results.append(result)

            if result.get('success'):
                file_size = result.get('file_size_mb', 0)
                time_sec = result.get('conversion_time_seconds', 0)
                print(f"✅ Method {method}: {file_size:.2f}MB, {time_sec:.1f}s")
            else:
                print(f"❌ Method {method}: FAILED")

        return results

    def run_duration_tests(self) -> List[Dict[str, Any]]:
        """Test các độ dài video khác nhau"""
        print("\n⏰ Testing Different Durations...")

        durations = [1, 2, 3, 5, 8, 10, 15]
        results = []
        base_config = {"quality": 75, "method": 4, "fps": 15, "width": 480, "height": 360}

        for duration in durations:
            name = f"duration_{duration}s"
            output_path = self.output_dir / f"{name}.webp"

            config = {**base_config, "duration": duration}

            print(f"\n⏰ Testing: {duration} seconds")
            # result = self.converter.convert(  # Module not found
            #     input_path=self.input_video,
            #     output_path=str(output_path),
            #     verbose=False,
            #     **config
            # )
            result = {"success": False, "error": "VideoToWebPConverter not available"}

            result["test_name"] = name
            result["config"] = config
            results.append(result)

            if result.get('success'):
                print(f"✅ {duration}s: {result.get('file_size_mb', 0):.2f}MB, {result.get('frames', 0)} frames")
            else:
                print(f"❌ {duration}s: FAILED")

        return results

    def generate_comparison_report(self, all_results: List[Dict[str, Any]]) -> str:
        """Tạo báo cáo so sánh chi tiết"""
        report_path = self.output_dir / "comparison_report.json"

        # Tính toán thống kê
        successful_results = [r for r in all_results if r.get('success')]

        if not successful_results:
            print("❌ No successful conversions to analyze")
            return str(report_path)

        # Tìm best performers
        smallest_file = min(successful_results, key=lambda x: x.get('file_size_mb', float('inf')))
        fastest_conversion = min(successful_results, key=lambda x: x.get('conversion_time_seconds', float('inf')))
        highest_quality = max(successful_results, key=lambda x: x.get('config', {}).get('quality', 0))

        summary = {
            "test_summary": {
                "total_tests": len(all_results),
                "successful_tests": len(successful_results),
                "failed_tests": len(all_results) - len(successful_results),
                "input_file": self.input_video,
                "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "best_performers": {
                "smallest_file": {
                    "test_name": smallest_file.get('test_name'),
                    "file_size_mb": smallest_file.get('file_size_mb'),
                    "config": smallest_file.get('config')
                },
                "fastest_conversion": {
                    "test_name": fastest_conversion.get('test_name'),
                    "conversion_time_seconds": fastest_conversion.get('conversion_time_seconds'),
                    "config": fastest_conversion.get('config')
                },
                "highest_quality": {
                    "test_name": highest_quality.get('test_name'),
                    "quality": highest_quality.get('config', {}).get('quality'),
                    "config": highest_quality.get('config')
                }
            },
            "detailed_results": all_results
        }

        # Lưu report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # In summary
        print("\n" + "="*80)
        print("📊 FINAL COMPARISON REPORT")
        print("="*80)
        print(f"✅ Total Tests: {summary['test_summary']['total_tests']}")
        print(f"✅ Successful: {summary['test_summary']['successful_tests']}")
        print(f"❌ Failed: {summary['test_summary']['failed_tests']}")
        print(f"\n🏆 BEST PERFORMERS:")
        print(f"📁 Smallest File: {smallest_file.get('test_name')} ({smallest_file.get('file_size_mb'):.2f}MB)")
        print(f"⚡ Fastest: {fastest_conversion.get('test_name')} ({fastest_conversion.get('conversion_time_seconds'):.1f}s)")
        print(f"🎨 Highest Quality: {highest_quality.get('test_name')} (Q{highest_quality.get('config', {}).get('quality', 0)})")
        print(f"\n📄 Full report: {report_path}")
        print("="*80)

        return str(report_path)

    def run_all_tests(self):
        """Chạy tất cả các test"""
        print(f"🚀 Starting WebP Test Suite for: {self.input_video}")
        print(f"📂 Output directory: {self.output_dir}")

        all_results = []

        # Chạy các test
        all_results.extend(self.run_preset_tests())
        all_results.extend(self.run_size_comparison_tests())
        all_results.extend(self.run_fps_comparison_tests())
        all_results.extend(self.run_quality_comparison_tests())
        all_results.extend(self.run_method_comparison_tests())
        all_results.extend(self.run_duration_tests())

        # Tạo báo cáo
        report_path = self.generate_comparison_report(all_results)

        return all_results, report_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="WebP Test Suite - Batch testing different configurations"
    )
    parser.add_argument("input", help="Input video file")
    parser.add_argument("--output-dir", default="webp_tests", help="Output directory")
    parser.add_argument("--test", choices=[
        "all", "presets", "sizes", "fps", "quality", "methods", "duration"
    ], default="all", help="Which tests to run")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        return 1

    suite = WebPTestSuite(args.input, args.output_dir)

    if args.test == "all":
        suite.run_all_tests()
    elif args.test == "presets":
        results = suite.run_preset_tests()
        suite.generate_comparison_report(results)
    elif args.test == "sizes":
        results = suite.run_size_comparison_tests()
        suite.generate_comparison_report(results)
    elif args.test == "fps":
        results = suite.run_fps_comparison_tests()
        suite.generate_comparison_report(results)
    elif args.test == "quality":
        results = suite.run_quality_comparison_tests()
        suite.generate_comparison_report(results)
    elif args.test == "methods":
        results = suite.run_method_comparison_tests()
        suite.generate_comparison_report(results)
    elif args.test == "duration":
        results = suite.run_duration_tests()
        suite.generate_comparison_report(results)

    return 0


if __name__ == "__main__":
    exit(main())
