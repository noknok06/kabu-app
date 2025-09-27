# stock/management/commands/fix_dependencies.py
from django.core.management.base import BaseCommand
import subprocess
import sys

class Command(BaseCommand):
    help = '必要な依存関係を自動インストール'
    
    def handle(self, *args, **options):
        self.stdout.write('依存関係の確認とインストールを開始...')
        
        required_packages = [
            'xlrd>=2.0.1',
            'openpyxl>=3.0.0',
            'lxml>=4.9.0',
        ]
        
        for package in required_packages:
            try:
                self.stdout.write(f'インストール中: {package}')
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package
                ])
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {package} インストール完了')
                )
            except subprocess.CalledProcessError as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ {package} インストール失敗: {e}')
                )
        
        self.stdout.write('\n依存関係の確認結果:')
        
        # インストールされたパッケージの確認
        packages_to_check = ['xlrd', 'openpyxl', 'lxml', 'pandas', 'yfinance']
        
        for package in packages_to_check:
            try:
                module = __import__(package)
                version = getattr(module, '__version__', 'バージョン不明')
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {package}: {version}')
                )
            except ImportError:
                self.stdout.write(
                    self.style.ERROR(f'✗ {package}: インストールされていません')
                )
        
        self.stdout.write('\n次のステップ:')
        self.stdout.write('1. python manage.py create_sample_stock')
        self.stdout.write('2. python manage.py update_indicators --limit 5')
        self.stdout.write('3. python manage.py runserver')