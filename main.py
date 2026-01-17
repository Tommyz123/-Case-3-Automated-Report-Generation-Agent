#!/usr/bin/env python3
"""
Case 3 自动化报告生成系统 - 命令行入口

用法:
    # 为单个公司生成报告
    python main.py --company EmergConnect

    # 批量生成所有公司报告
    python main.py --batch

    # 列出可用的公司
    python main.py --list

    # 指定输出路径
    python main.py --company EmergConnect --output output/custom_report.docx
"""

import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def get_api_config():
    """从环境变量获取 API 配置"""
    from src.ai_generator import APIConfig

    # 优先使用OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return APIConfig(
            api_key=openai_key,
            endpoint=os.getenv("OPENAI_ENDPOINT", ""),
            model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_tokens=int(os.getenv("MAX_TOKENS", "4000"))
        )
    
    # 否则使用Claude
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("错误: 未设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量")
        print("请在 .env 文件中配置您的 API 密钥")
        sys.exit(1)

    return APIConfig(
        api_key=api_key,
        endpoint=os.getenv("ANTHROPIC_ENDPOINT", "https://api.anthropic.com/v1"),
        model_name=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        max_tokens=int(os.getenv("MAX_TOKENS", "4000"))
    )


def list_companies():
    """列出所有可用的公司"""
    from src.data_extractor import DataExtractor

    print("\n可用的公司列表:")
    print("-" * 40)

    extractor = DataExtractor("data")

    # 从 SDG 问卷中获取公司
    try:
        sdg_data = extractor.extract_sdg_questionnaire("SDG问卷调查_完整中文版.xlsx")
        companies_from_sdg = set(item.company_name for item in sdg_data if item.company_name)
        print(f"\nSDG问卷中的公司 ({len(companies_from_sdg)}个):")
        for company in sorted(companies_from_sdg):
            print(f"  - {company}")
    except Exception as e:
        print(f"警告: 无法读取SDG问卷 - {e}")

    # 从影响机制中获取公司
    try:
        impact_data = extractor.extract_impact_mechanisms("影响评估机制_完整中文版.xlsx")
        companies_from_impact = set(item.company_name for item in impact_data if item.company_name)
        print(f"\n影响机制数据中的公司 ({len(companies_from_impact)}个):")
        for company in sorted(companies_from_impact):
            print(f"  - {company}")
    except Exception as e:
        print(f"警告: 无法读取影响机制数据 - {e}")

    print()


def generate_single_report(company_name: str, output_path: str = None):
    """为单个公司生成报告"""
    from src.orchestrator import ReportOrchestrator

    print(f"\n正在为 {company_name} 生成报告...")
    print("-" * 40)

    api_config = get_api_config()

    orchestrator = ReportOrchestrator(
        data_dir="data",
        config_path="config/template_mapping.yaml",
        api_config=api_config
    )

    try:
        result = orchestrator.generate_report(
            company_name=company_name,
            output_path=output_path
        )

        if result.success:
            print(f"\n报告生成成功!")
            print(f"  报告文件: {result.output_path}")
            if result.metrics:
                print(f"  生成时间: {result.metrics.get('generation_time_seconds', 'N/A')}秒")
                print(f"  Token使用: {result.metrics.get('total_tokens', 'N/A')}")
            return True
        else:
            print(f"\n报告生成失败:")
            for error in result.validation_errors:
                print(f"  - {error}")
            return False

    except Exception as e:
        print(f"\n错误: 报告生成失败 - {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_batch_reports():
    """批量生成所有公司的报告"""
    from src.data_extractor import DataExtractor

    print("\n开始批量生成报告...")
    print("-" * 40)

    extractor = DataExtractor("data")

    # 获取所有公司
    try:
        impact_data = extractor.extract_impact_mechanisms("影响评估机制_完整中文版.xlsx")
        companies = list(set(item.company_name for item in impact_data if item.company_name))
    except Exception as e:
        print(f"错误: 无法获取公司列表 - {e}")
        return

    print(f"找到 {len(companies)} 个公司")

    success_count = 0
    failed_companies = []

    for i, company in enumerate(companies, 1):
        print(f"\n[{i}/{len(companies)}] 处理: {company}")
        try:
            if generate_single_report(company):
                success_count += 1
            else:
                failed_companies.append(company)
        except Exception as e:
            print(f"  失败: {e}")
            failed_companies.append(company)

    print("\n" + "=" * 40)
    print(f"批量生成完成:")
    print(f"  成功: {success_count}/{len(companies)}")
    if failed_companies:
        print(f"  失败: {', '.join(failed_companies)}")


def main():
    parser = argparse.ArgumentParser(
        description="Case 3 自动化报告生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python main.py --list                          列出所有可用的公司
    python main.py --company EmergConnect          为 EmergConnect 生成报告
    python main.py --company EmergConnect -o out.docx  指定输出文件
    python main.py --batch                         批量生成所有公司报告
        """
    )

    parser.add_argument(
        "--company", "-c",
        type=str,
        help="要生成报告的公司名称"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出文件路径 (默认: output/<公司名>_report.docx)"
    )

    parser.add_argument(
        "--batch", "-b",
        action="store_true",
        help="批量生成所有公司的报告"
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出所有可用的公司"
    )

    args = parser.parse_args()

    # 切换到项目目录
    project_dir = Path(__file__).parent
    os.chdir(project_dir)

    print("=" * 50)
    print("Case 3 自动化报告生成系统")
    print("=" * 50)

    if args.list:
        list_companies()
    elif args.batch:
        generate_batch_reports()
    elif args.company:
        generate_single_report(args.company, args.output)
    else:
        parser.print_help()
        print("\n提示: 使用 --list 查看可用的公司列表")


if __name__ == "__main__":
    main()
