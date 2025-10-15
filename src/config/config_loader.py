"""
설정 파일 로더

.env 파일에서 환경변수를 로드하고,
config.yaml의 환경변수 참조를 실제 값으로 치환합니다.
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """설정 파일 로더 클래스"""
    
    def __init__(self, config_path: str = None, env_path: str = None):
        """
        ConfigLoader 초기화
        
        Args:
            config_path (str): config.yaml 파일 경로
            env_path (str): .env 파일 경로
        """
        # 프로젝트 루트 디렉토리 찾기
        self.project_root = self._find_project_root()
        
        # 기본 경로 설정
        if config_path is None:
            config_path = self.project_root / 'src' / 'config' / 'config.yaml'
        if env_path is None:
            env_path = self.project_root / '.env'
            
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        
        # .env 파일 로드
        self._load_env_file()
        
    def _find_project_root(self) -> Path:
        """
        프로젝트 루트 디렉토리 찾기 (.env 파일이 있는 위치)
        
        Returns:
            Path: 프로젝트 루트 경로
        """
        current = Path(__file__).resolve().parent
        
        # 상위 디렉토리로 올라가면서 .env 파일 찾기
        while current != current.parent:
            if (current / '.env').exists() or (current / 'pyproject.toml').exists():
                return current
            current = current.parent
            
        # 찾지 못한 경우 현재 파일의 3단계 상위 디렉토리 (src/config 기준)
        return Path(__file__).resolve().parent.parent.parent
    
    def _load_env_file(self):
        """
        .env 파일에서 환경변수 로드
        """
        if not self.env_path.exists():
            print(f"⚠️  Warning: .env file not found at {self.env_path}")
            print(f"    Please copy .env.example to .env and fill in your credentials.")
            return
            
        with open(self.env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 빈 줄이나 주석 무시
                if not line or line.startswith('#'):
                    continue
                    
                # KEY=VALUE 형태 파싱
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 기존 환경변수가 없을 때만 설정 (기존 환경변수 우선)
                    if key not in os.environ:
                        os.environ[key] = value
    
    def _replace_env_vars(self, value: Any) -> Any:
        """
        값에서 환경변수 참조(${VAR_NAME})를 실제 값으로 치환
        
        Args:
            value: 치환할 값 (str, dict, list 등)
            
        Returns:
            치환된 값
        """
        if isinstance(value, str):
            # ${VAR_NAME} 패턴 찾기
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            for var_name in matches:
                env_value = os.environ.get(var_name, '')
                if not env_value:
                    print(f"⚠️  Warning: Environment variable {var_name} is not set")
                value = value.replace(f'${{{var_name}}}', env_value)
            
            return value
            
        elif isinstance(value, dict):
            return {k: self._replace_env_vars(v) for k, v in value.items()}
            
        elif isinstance(value, list):
            return [self._replace_env_vars(item) for item in value]
            
        else:
            return value
    
    def load_config(self) -> Dict[str, Any]:
        """
        설정 파일 로드 및 환경변수 치환
        
        Returns:
            Dict: 설정 딕셔너리
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 환경변수 치환
        config = self._replace_env_vars(config)
        
        # TRADE_MODE 환경변수로 오버라이드
        if 'TRADE_MODE' in os.environ:
            config['trade_mode'] = os.environ['TRADE_MODE']
        
        return config
    
    def get_api_credentials(self) -> Dict[str, str]:
        """
        현재 거래 모드에 맞는 API 인증 정보 반환
        
        Returns:
            Dict: API 인증 정보 (api_key, secret_key, account_id, htsid)
        """
        config = self.load_config()
        mode = config['trade_mode']
        
        if mode not in ['simulation', 'real']:
            raise ValueError(f"Invalid trade_mode: {mode}. Must be 'simulation' or 'real'")
        
        credentials = config[mode].copy()
        credentials['mode'] = mode
        
        return credentials


# 싱글톤 인스턴스
_config_loader = None

def get_config_loader() -> ConfigLoader:
    """
    ConfigLoader 싱글톤 인스턴스 반환
    
    Returns:
        ConfigLoader: 설정 로더 인스턴스
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config() -> Dict[str, Any]:
    """
    설정 파일 로드 (간편 함수)
    
    Returns:
        Dict: 설정 딕셔너리
    """
    return get_config_loader().load_config()


def get_api_credentials() -> Dict[str, str]:
    """
    API 인증 정보 반환 (간편 함수)
    
    Returns:
        Dict: API 인증 정보
    """
    return get_config_loader().get_api_credentials()
