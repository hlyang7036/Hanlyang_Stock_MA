"""
청산 신호 생성 모듈

이 모듈은 3단계 청산 시스템을 통해 포지션 청산 신호를 생성합니다.

Functions:
    generate_exit_signal: 청산 신호 생성 (3단계 통합)
    check_histogram_peakout: 히스토그램 피크아웃 확인 (1단계)
    check_macd_peakout: MACD선 피크아웃 확인 (2단계)
    check_macd_cross: MACD-시그널 교차 확인 (3단계)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
from src.analysis.technical.indicators import detect_peakout

logger = logging.getLogger(__name__)


def check_histogram_peakout(
    data: pd.DataFrame,
    position_type: str
) -> pd.Series:
    """
    히스토그램 피크아웃 확인 (1단계)
    
    Args:
        data: DataFrame (Histogram 컬럼 필요)
        position_type: 'long' (매수) or 'short' (매도)
        lookback: 피크아웃 감지 기간 (기본값: 3)
    
    Returns:
        pd.Series: 피크아웃 발생 여부 (boolean)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때
    
    Notes:
        매수 포지션: 히스토그램이 고점 대비 하락 (하락 피크아웃)
        매도 포지션: 히스토그램이 저점 대비 상승 (상승 피크아웃)
        
        Level 2의 detect_peakout() 활용
        - 반환값: 1 (고점 피크아웃), -1 (저점 피크아웃), 0 (없음)
    
    Examples:
        >>> peakout = check_histogram_peakout(df, 'long')
        >>> exit_points = df[peakout]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    if 'Histogram' not in data.columns:
        raise ValueError("Histogram 컬럼이 필요합니다")
    
    logger.debug(f"히스토그램 피크아웃 체크: {position_type}, {len(data)}개 데이터")
    
    # Level 2의 detect_peakout 활용
    # 매수 포지션: 하락 피크아웃
    # 매도 포지션: 상승 피크아웃
    direction = 'down' if position_type == 'long' else 'up'
    
    peakout = detect_peakout(data['Histogram'], direction=direction)
    
    # 통계 로깅
    peakout_count = peakout.sum()
    if peakout_count > 0:
        logger.info(f"히스토그램 피크아웃 발생: {peakout_count}회 ({position_type})")
    else:
        logger.debug(f"히스토그램 피크아웃 없음 ({position_type})")
    
    return peakout


def check_macd_peakout(
    data: pd.DataFrame,
    position_type: str,
    macd_column: str = 'MACD'
) -> pd.Series:
    """
    MACD선 피크아웃 확인 (2단계)
    
    Args:
        data: DataFrame (MACD 컬럼 필요)
        position_type: 'long' or 'short'
        macd_column: MACD 컬럼 이름 (기본값: 'MACD')
    
    Returns:
        pd.Series: 피크아웃 발생 여부 (boolean)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때
    
    Notes:
        매수 포지션: MACD선이 고점 대비 하락
        매도 포지션: MACD선이 저점 대비 상승
    
    Examples:
        >>> peakout = check_macd_peakout(df, 'long')
        >>> exit_50_points = df[peakout]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    if macd_column not in data.columns:
        raise ValueError(f"{macd_column} 컬럼이 필요합니다")
    
    logger.debug(f"MACD선 피크아웃 체크: {position_type}, {len(data)}개 데이터")
    
    # 방향 결정
    direction = 'down' if position_type == 'long' else 'up'
    
    peakout = detect_peakout(data[macd_column], direction=direction)
    
    # 통계 로깅
    peakout_count = peakout.sum()
    if peakout_count > 0:
        logger.info(f"MACD선 피크아웃 발생: {peakout_count}회 ({position_type})")
    else:
        logger.debug(f"MACD선 피크아웃 없음 ({position_type})")
    
    return peakout


def check_macd_cross(
    data: pd.DataFrame,
    position_type: str,
    macd_column: str = 'MACD',
    signal_column: str = 'Signal'
) -> pd.Series:
    """
    MACD-시그널 교차 확인 (3단계)
    
    Args:
        data: DataFrame (MACD, Signal 컬럼 필요)
        position_type: 'long' or 'short'
        macd_column: MACD 컬럼 이름 (기본값: 'MACD')
        signal_column: 시그널 컬럼 이름 (기본값: 'Signal')
    
    Returns:
        pd.Series: 교차 발생 여부 (boolean)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때
    
    Notes:
        매수 포지션: 데드크로스 발생 (MACD < Signal로 교차)
        매도 포지션: 골든크로스 발생 (MACD > Signal로 교차)
    
    Examples:
        >>> cross = check_macd_cross(df, 'long')
        >>> exit_100_points = df[cross]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    required_columns = [macd_column, signal_column]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"MACD-시그널 교차 체크: {position_type}, {len(data)}개 데이터")
    
    # NaN이 아닌 값만 사용 (forward fill 사용)
    macd_values = data[macd_column].ffill()
    signal_values = data[signal_column].ffill()
    
    # 현재 및 이전 관계 (boolean)
    current_above = (macd_values > signal_values).astype(bool)
    prev_above = current_above.shift(1).astype(bool)
    
    # 교차 감지
    if position_type == 'long':
        # 데드크로스: MACD가 Signal 위 → 아래로
        cross = prev_above & (~current_above)
    else:  # short
        # 골든크로스: MACD가 Signal 아래 → 위로
        cross = (~prev_above) & current_above
    
    # 첫 행은 비교 불가
    cross.iloc[0] = False
    
    # NaN 처리
    cross = cross.fillna(False).astype(bool)
    
    # 통계 로깅
    cross_count = cross.sum()
    cross_type = "데드크로스" if position_type == 'long' else "골든크로스"
    if cross_count > 0:
        logger.info(f"{cross_type} 발생: {cross_count}회 ({position_type})")
    else:
        logger.debug(f"{cross_type} 없음 ({position_type})")
    
    return cross


def generate_exit_signal(
    data: pd.DataFrame,
    position_type: str,
    macd_column: str = 'MACD',
    signal_column: str = 'Signal'
) -> pd.DataFrame:
    """
    청산 신호 생성 (3단계)
    
    Args:
        data: DataFrame (MACD, Histogram, Signal 필요)
        position_type: 'long' (매수 포지션) 또는 'short' (매도 포지션)
        macd_column: MACD 컬럼 이름 (기본값: 'MACD')
        signal_column: 시그널 컬럼 이름 (기본값: 'Signal')
    
    Returns:
        pd.DataFrame: 청산 신호
            - Exit_Level: 청산 레벨 (0: 없음, 1: 경계, 2: 50%, 3: 100%)
            - Exit_Percentage: 청산 비율 (0, 0, 50, 100)
            - Exit_Reason: 청산 이유
            - Should_Exit: 청산 여부 (boolean)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때
    
    Notes:
        청산 3단계:
        1. 히스토그램 피크아웃 → 경계 태세 (0% 청산)
        2. MACD선 피크아웃 → 50% 청산
        3. MACD-시그널 교차 → 100% 청산
        
        우선순위: 3단계 > 2단계 > 1단계
    
    Examples:
        >>> exit_signals = generate_exit_signal(df, 'long')
        >>> # 50% 청산 지점
        >>> exit_50 = df[exit_signals['Exit_Level'] == 2]
        >>> # 100% 청산 지점
        >>> exit_100 = df[exit_signals['Exit_Level'] == 3]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")
    
    required_columns = ['Histogram', macd_column, signal_column]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"청산 신호 생성 시작: {position_type}, {len(data)}개 데이터")
    
    # 결과 DataFrame 초기화
    result = pd.DataFrame(index=data.index)
    result['Exit_Level'] = 0
    result['Exit_Percentage'] = 0
    result['Exit_Reason'] = ''
    result['Should_Exit'] = False
    
    # 1단계: 히스토그램 피크아웃
    hist_peakout = check_histogram_peakout(data, position_type)
    result.loc[hist_peakout, 'Exit_Level'] = 1
    result.loc[hist_peakout, 'Exit_Percentage'] = 0
    result.loc[hist_peakout, 'Exit_Reason'] = '1단계: 히스토그램 피크아웃 (경계)'
    result.loc[hist_peakout, 'Should_Exit'] = False  # 경계만, 청산 X
    
    # 2단계: MACD선 피크아웃 (우선순위 높음)
    macd_peakout = check_macd_peakout(data, position_type, macd_column)
    result.loc[macd_peakout, 'Exit_Level'] = 2
    result.loc[macd_peakout, 'Exit_Percentage'] = 50
    result.loc[macd_peakout, 'Exit_Reason'] = '2단계: MACD선 피크아웃 (50% 청산)'
    result.loc[macd_peakout, 'Should_Exit'] = True
    
    # 3단계: MACD-시그널 교차 (최우선)
    macd_cross = check_macd_cross(data, position_type, macd_column, signal_column)
    result.loc[macd_cross, 'Exit_Level'] = 3
    result.loc[macd_cross, 'Exit_Percentage'] = 100
    cross_type = "데드크로스" if position_type == 'long' else "골든크로스"
    result.loc[macd_cross, 'Exit_Reason'] = f'3단계: {cross_type} (100% 청산)'
    result.loc[macd_cross, 'Should_Exit'] = True
    
    # 통계 로깅
    level_counts = result['Exit_Level'].value_counts().sort_index()
    logger.info(f"청산 신호 생성 완료 ({position_type}):")
    for level in [1, 2, 3]:
        count = level_counts.get(level, 0)
        if count > 0:
            logger.info(f"  레벨 {level}: {count}회")
    
    total_exit = result['Should_Exit'].sum()
    logger.info(f"실제 청산 필요: {total_exit}회")
    
    logger.debug("청산 신호 생성 완료")
    
    return result
