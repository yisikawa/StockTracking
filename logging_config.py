"""ロギング設定モジュール"""
import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logging(app):
    """アプリケーションのロギングを設定"""
    if app.debug:
        return
    
    try:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/app.log', 
            maxBytes=10240, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)
        
        app.logger.info('Logging configured successfully')
        
    except PermissionError:
        print("警告: ログファイルへの書き込み権限がありません。標準出力のみを使用します。")
    except Exception as e:
        print(f"警告: ログ設定中にエラーが発生しました: {e}")
