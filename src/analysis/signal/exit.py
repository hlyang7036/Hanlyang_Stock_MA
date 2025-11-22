"""
청산 신호 생성 모듈

이 모듈은 3중 MACD 시스템 기반 청산 신호를 생성합니다.

Functions:
    generate_exit_signal: 청산 신호 생성 (3중 MACD 통합)
    check_single_macd_exit: 단일 MACD의 청산 신호 계산
    check_histogram_peakout: 히스토그램 피크아웃 확인
    check_macd_peakout: MACD선 피크아웃 확인
    check_macd_cross: MACD-시그널 교차 확인
    merge_sequential: 순차적 다단계 청산
    merge_fastest: 가장 빠른 MACD 사용
    merge_slowest: 가장 느린 MACD 사용
    merge_majority: 다수결 청산
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
from src.analysis.technical.indicators import detect_peakout

logger = logging.getLogger(__name__)


def check_histogram_peakout(
    data: pd.DataFrame,
    position_type: str,
    hist_col: str = 'Histogram'
) -> pd.Series:
    """
    히스토그램 피크아웃 확인 (1단계)

    Args:
        data: DataFrame
        position_type: 'long' (매수) or 'short' (매도)
        hist_col: 히스토그램 컬럼 이름 (기본값: 'Histogram')

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
        >>> peakout = check_histogram_peakout(df, 'long', 'Histogram_상')
        >>> exit_points = df[peakout]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")

    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")

    if hist_col not in data.columns:
        raise ValueError(f"{hist_col} 컬럼이 필요합니다")

    logger.debug(f"히스토그램 피크아웃 체크: {position_type}, {hist_col}, {len(data)}개 데이터")

    # Level 2의 detect_peakout 활용
    # 매수 포지션: 하락 피크아웃
    # 매도 포지션: 상승 피크아웃
    direction = 'down' if position_type == 'long' else 'up'

    peakout = detect_peakout(data[hist_col], direction=direction)

    # 통계 로깅
    peakout_count = peakout.sum()
    if peakout_count > 0:
        logger.debug(f"히스토그램 피크아웃 발생: {peakout_count}회 ({hist_col})")

    return peakout


def check_macd_peakout(
    data: pd.DataFrame,
    position_type: str,
    macd_col: str = 'MACD'
) -> pd.Series:
    """
    MACD선 피크아웃 확인 (2단계)

    Args:
        data: DataFrame
        position_type: 'long' or 'short'
        macd_col: MACD 컬럼 이름 (기본값: 'MACD')

    Returns:
        pd.Series: 피크아웃 발생 여부 (boolean)

    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때

    Notes:
        매수 포지션: MACD선이 고점 대비 하락
        매도 포지션: MACD선이 저점 대비 상승

    Examples:
        >>> peakout = check_macd_peakout(df, 'long', 'MACD_상')
        >>> exit_50_points = df[peakout]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")

    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")

    if macd_col not in data.columns:
        raise ValueError(f"{macd_col} 컬럼이 필요합니다")

    logger.debug(f"MACD선 피크아웃 체크: {position_type}, {macd_col}, {len(data)}개 데이터")

    # 방향 결정
    direction = 'down' if position_type == 'long' else 'up'

    peakout = detect_peakout(data[macd_col], direction=direction)

    # 통계 로깅
    peakout_count = peakout.sum()
    if peakout_count > 0:
        logger.debug(f"MACD선 피크아웃 발생: {peakout_count}회 ({macd_col})")

    return peakout


def check_macd_cross(
    data: pd.DataFrame,
    position_type: str,
    macd_col: str = 'MACD',
    signal_col: str = 'Signal'
) -> pd.Series:
    """
    MACD-시그널 교차 확인 (3단계)

    Args:
        data: DataFrame
        position_type: 'long' or 'short'
        macd_col: MACD 컬럼 이름 (기본값: 'MACD')
        signal_col: 시그널 컬럼 이름 (기본값: 'Signal')

    Returns:
        pd.Series: 교차 발생 여부 (boolean)

    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때

    Notes:
        매수 포지션: 데드크로스 발생 (MACD < Signal로 교차)
        매도 포지션: 골든크로스 발생 (MACD > Signal로 교차)

    Examples:
        >>> cross = check_macd_cross(df, 'long', 'MACD_하', 'Signal_하')
        >>> exit_100_points = df[cross]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")

    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")

    required_columns = [macd_col, signal_col]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")

    logger.debug(f"MACD-시그널 교차 체크: {position_type}, {macd_col}/{signal_col}, {len(data)}개 데이터")

    # NaN이 아닌 값만 사용 (forward fill 사용)
    macd_values = data[macd_col].ffill()
    signal_values = data[signal_col].ffill()

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
    if cross_count > 0:
        cross_type = "데드크로스" if position_type == 'long' else "골든크로스"
        logger.debug(f"{cross_type} 발생: {cross_count}회 ({macd_col})")

    return cross


def check_single_macd_exit(
    data: pd.DataFrame,
    position_type: str,
    macd_col: str,
    signal_col: str,
    hist_col: str
) -> Dict[str, pd.Series]:
    """
    단일 MACD의 청산 신호 계산

    Args:
        data: DataFrame
        position_type: 'long' or 'short'
        macd_col: MACD 컬럼 이름
        signal_col: Signal 컬럼 이름
        hist_col: Histogram 컬럼 이름

    Returns:
        Dict: 3가지 청산 신호
            - 'histogram_peakout': 히스토그램 피크아웃
            - 'macd_peakout': MACD 피크아웃
            - 'macd_cross': MACD-Signal 교차

    Examples:
        >>> exit_signals = check_single_macd_exit(
        ...     df, 'long', 'MACD_상', 'Signal_상', 'Histogram_상'
        ... )
        >>> exit_signals['histogram_peakout']
    """
    return {
        'histogram_peakout': check_histogram_peakout(data, position_type, hist_col),
        'macd_peakout': check_macd_peakout(data, position_type, macd_col),
        'macd_cross': check_macd_cross(data, position_type, macd_col, signal_col)
    }


def merge_sequential(
    exit_fast: Dict[str, pd.Series],
    exit_mid: Dict[str, pd.Series],
    exit_slow: Dict[str, pd.Series],
    data: pd.DataFrame
) -> pd.DataFrame:
    """
    순차적 다단계 청산 로직

    - MACD_상 histogram 피크아웃 → Level 1 (0% 청산, 경계)
    - MACD_중 MACD 피크아웃 → Level 2 (50% 청산)
    - MACD_하 cross → Level 3 (100% 청산)

    Args:
        exit_fast: 빠른 MACD (MACD_상) 신호
        exit_mid: 중간 MACD (MACD_중) 신호
        exit_slow: 느린 MACD (MACD_하) 신호
        data: 원본 DataFrame (index 참조용)

    Returns:
        pd.DataFrame: 통합 청산 신호
            - Exit_Level: 0~3
            - Exit_Ratio: 0, 0, 50, 100
            - Exit_Reason: 청산 이유
            - Exit_Signal: 어떤 MACD에서 발생했는지

    Notes:
        우선순위: Level 3 > Level 2 > Level 1
    """
    result = pd.DataFrame(index=data.index)
    result['Exit_Level'] = 0
    result['Exit_Ratio'] = 0
    result['Exit_Reason'] = ''
    result['Exit_Signal'] = ''

    # Level 1: MACD_상 히스토그램 피크아웃
    hist_fast = exit_fast['histogram_peakout']
    result.loc[hist_fast, 'Exit_Level'] = 1
    result.loc[hist_fast, 'Exit_Ratio'] = 0
    result.loc[hist_fast, 'Exit_Reason'] = '1단계: MACD_상 히스토그램 피크아웃 (경계)'
    result.loc[hist_fast, 'Exit_Signal'] = 'MACD_상'

    # Level 2: MACD_중 MACD 라인 피크아웃
    macd_mid = exit_mid['macd_peakout']
    result.loc[macd_mid, 'Exit_Level'] = 2
    result.loc[macd_mid, 'Exit_Ratio'] = 50
    result.loc[macd_mid, 'Exit_Reason'] = '2단계: MACD_중 피크아웃 (50% 청산)'
    result.loc[macd_mid, 'Exit_Signal'] = 'MACD_중'

    # Level 3: MACD_하 크로스
    cross_slow = exit_slow['macd_cross']
    result.loc[cross_slow, 'Exit_Level'] = 3
    result.loc[cross_slow, 'Exit_Ratio'] = 100
    result.loc[cross_slow, 'Exit_Reason'] = '3단계: MACD_하 교차 (100% 청산)'
    result.loc[cross_slow, 'Exit_Signal'] = 'MACD_하'

    return result


def merge_fastest(
    exit_fast: Dict[str, pd.Series],
    data: pd.DataFrame
) -> pd.DataFrame:
    """
    가장 빠른 MACD (MACD_상)만 사용

    Args:
        exit_fast: MACD_상 신호
        data: 원본 DataFrame

    Returns:
        pd.DataFrame: 청산 신호
    """
    result = pd.DataFrame(index=data.index)
    result['Exit_Level'] = 0
    result['Exit_Ratio'] = 0
    result['Exit_Reason'] = ''
    result['Exit_Signal'] = ''

    # Level 1: 히스토그램
    hist = exit_fast['histogram_peakout']
    result.loc[hist, 'Exit_Level'] = 1
    result.loc[hist, 'Exit_Ratio'] = 0
    result.loc[hist, 'Exit_Reason'] = '1단계: 히스토그램 피크아웃 (경계)'
    result.loc[hist, 'Exit_Signal'] = 'MACD_상'

    # Level 2: MACD 피크아웃
    macd = exit_fast['macd_peakout']
    result.loc[macd, 'Exit_Level'] = 2
    result.loc[macd, 'Exit_Ratio'] = 50
    result.loc[macd, 'Exit_Reason'] = '2단계: MACD 피크아웃 (50% 청산)'
    result.loc[macd, 'Exit_Signal'] = 'MACD_상'

    # Level 3: 크로스
    cross = exit_fast['macd_cross']
    result.loc[cross, 'Exit_Level'] = 3
    result.loc[cross, 'Exit_Ratio'] = 100
    result.loc[cross, 'Exit_Reason'] = '3단계: 교차 (100% 청산)'
    result.loc[cross, 'Exit_Signal'] = 'MACD_상'

    return result


def merge_slowest(
    exit_slow: Dict[str, pd.Series],
    data: pd.DataFrame
) -> pd.DataFrame:
    """
    가장 느린 MACD (MACD_하)만 사용

    Args:
        exit_slow: MACD_하 신호
        data: 원본 DataFrame

    Returns:
        pd.DataFrame: 청산 신호
    """
    result = pd.DataFrame(index=data.index)
    result['Exit_Level'] = 0
    result['Exit_Ratio'] = 0
    result['Exit_Reason'] = ''
    result['Exit_Signal'] = ''

    # Level 1: 히스토그램
    hist = exit_slow['histogram_peakout']
    result.loc[hist, 'Exit_Level'] = 1
    result.loc[hist, 'Exit_Ratio'] = 0
    result.loc[hist, 'Exit_Reason'] = '1단계: 히스토그램 피크아웃 (경계)'
    result.loc[hist, 'Exit_Signal'] = 'MACD_하'

    # Level 2: MACD 피크아웃
    macd = exit_slow['macd_peakout']
    result.loc[macd, 'Exit_Level'] = 2
    result.loc[macd, 'Exit_Ratio'] = 50
    result.loc[macd, 'Exit_Reason'] = '2단계: MACD 피크아웃 (50% 청산)'
    result.loc[macd, 'Exit_Signal'] = 'MACD_하'

    # Level 3: 크로스
    cross = exit_slow['macd_cross']
    result.loc[cross, 'Exit_Level'] = 3
    result.loc[cross, 'Exit_Ratio'] = 100
    result.loc[cross, 'Exit_Reason'] = '3단계: 교차 (100% 청산)'
    result.loc[cross, 'Exit_Signal'] = 'MACD_하'

    return result


def merge_majority(
    exit_fast: Dict[str, pd.Series],
    exit_mid: Dict[str, pd.Series],
    exit_slow: Dict[str, pd.Series],
    data: pd.DataFrame
) -> pd.DataFrame:
    """
    다수결 방식 청산

    2개 이상의 MACD에서 같은 레벨 신호가 발생하면 청산

    Args:
        exit_fast: MACD_상 신호
        exit_mid: MACD_중 신호
        exit_slow: MACD_하 신호
        data: 원본 DataFrame

    Returns:
        pd.DataFrame: 청산 신호
    """
    result = pd.DataFrame(index=data.index)
    result['Exit_Level'] = 0
    result['Exit_Ratio'] = 0
    result['Exit_Reason'] = ''
    result['Exit_Signal'] = ''

    # Level 1: 히스토그램 (2개 이상)
    hist_count = (
        exit_fast['histogram_peakout'].astype(int) +
        exit_mid['histogram_peakout'].astype(int) +
        exit_slow['histogram_peakout'].astype(int)
    )
    hist_majority = hist_count >= 2
    result.loc[hist_majority, 'Exit_Level'] = 1
    result.loc[hist_majority, 'Exit_Ratio'] = 0
    result.loc[hist_majority, 'Exit_Reason'] = '1단계: 히스토그램 피크아웃 (다수결, 경계)'
    result.loc[hist_majority, 'Exit_Signal'] = '다수결'

    # Level 2: MACD 피크아웃 (2개 이상)
    macd_count = (
        exit_fast['macd_peakout'].astype(int) +
        exit_mid['macd_peakout'].astype(int) +
        exit_slow['macd_peakout'].astype(int)
    )
    macd_majority = macd_count >= 2
    result.loc[macd_majority, 'Exit_Level'] = 2
    result.loc[macd_majority, 'Exit_Ratio'] = 50
    result.loc[macd_majority, 'Exit_Reason'] = '2단계: MACD 피크아웃 (다수결, 50% 청산)'
    result.loc[macd_majority, 'Exit_Signal'] = '다수결'

    # Level 3: 크로스 (2개 이상)
    cross_count = (
        exit_fast['macd_cross'].astype(int) +
        exit_mid['macd_cross'].astype(int) +
        exit_slow['macd_cross'].astype(int)
    )
    cross_majority = cross_count >= 2
    result.loc[cross_majority, 'Exit_Level'] = 3
    result.loc[cross_majority, 'Exit_Ratio'] = 100
    result.loc[cross_majority, 'Exit_Reason'] = '3단계: 교차 (다수결, 100% 청산)'
    result.loc[cross_majority, 'Exit_Signal'] = '다수결'

    return result


def generate_exit_signal(
    data: pd.DataFrame,
    position_type: str,
    strategy: str = 'sequential'
) -> pd.DataFrame:
    """
    청산 신호 생성 (3중 MACD 통합)

    Args:
        data: DataFrame (필수 컬럼)
            - Hist_상, MACD_상, Signal_상
            - Hist_중, MACD_중, Signal_중
            - Hist_하, MACD_하, Signal_하
        position_type: 'long' (매수 포지션) 또는 'short' (매도 포지션)
        strategy: 청산 전략
            - 'sequential': 순차적 다단계 청산 (기본값, 추천)
            - 'fastest': MACD_상만 사용 (빠른 청산)
            - 'slowest': MACD_하만 사용 (확실한 청산)
            - 'majority': 2개 이상 일치 시 청산

    Returns:
        pd.DataFrame: 청산 신호
            - Exit_Level: 0~3 (0=없음, 1=경계, 2=50%, 3=100%)
            - Exit_Ratio: 0, 0, 50, 100
            - Exit_Reason: 청산 이유
            - Exit_Signal: 어떤 MACD에서 발생했는지

    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때

    Notes:
        3중 MACD 시스템:
        - MACD_상 (5|20|9): 빠른 신호
        - MACD_중 (5|40|9): 중간 신호
        - MACD_하 (20|40|9): 느린 신호

        순차적 청산 (strategy='sequential'):
        1. MACD_상 히스토그램 피크아웃 → Level 1 (경계)
        2. MACD_중 MACD 피크아웃 → Level 2 (50%)
        3. MACD_하 교차 → Level 3 (100%)

    Examples:
        >>> # 3중 MACD 데이터 준비 (Level 2에서 자동 계산됨)
        >>> exit_signals = generate_exit_signal(df, 'long', 'sequential')
        >>> # 50% 청산 지점
        >>> exit_50 = df[exit_signals['Exit_Level'] == 2]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")

    if position_type not in ['long', 'short']:
        raise ValueError(f"position_type은 'long' 또는 'short'여야 합니다: {position_type}")

    if strategy not in ['sequential', 'fastest', 'slowest', 'majority']:
        raise ValueError(f"strategy는 'sequential', 'fastest', 'slowest', 'majority' 중 하나여야 합니다: {strategy}")

    # 3중 MACD 필수 컬럼 확인
    required_columns = [
        'Hist_상', 'MACD_상', 'Signal_상',
        'Hist_중', 'MACD_중', 'Signal_중',
        'Hist_하', 'MACD_하', 'Signal_하'
    ]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")

    logger.debug(f"청산 신호 생성 시작: {position_type}, strategy={strategy}, {len(data)}개 데이터")

    # 각 MACD별 청산 신호 계산
    exit_fast = check_single_macd_exit(data, position_type, 'MACD_상', 'Signal_상', 'Hist_상')
    exit_mid = check_single_macd_exit(data, position_type, 'MACD_중', 'Signal_중', 'Hist_중')
    exit_slow = check_single_macd_exit(data, position_type, 'MACD_하', 'Signal_하', 'Hist_하')

    # strategy에 따라 통합
    if strategy == 'sequential':
        result = merge_sequential(exit_fast, exit_mid, exit_slow, data)
    elif strategy == 'fastest':
        result = merge_fastest(exit_fast, data)
    elif strategy == 'slowest':
        result = merge_slowest(exit_slow, data)
    elif strategy == 'majority':
        result = merge_majority(exit_fast, exit_mid, exit_slow, data)

    # Should_Exit 컬럼 추가 (Exit_Level >= 2일 때 True)
    result['Should_Exit'] = result['Exit_Level'] >= 2

    # 통계 로깅
    level_counts = result['Exit_Level'].value_counts().sort_index()
    logger.info(f"청산 신호 생성 완료 ({position_type}, {strategy}):")
    for level in [1, 2, 3]:
        count = level_counts.get(level, 0)
        if count > 0:
            logger.info(f"  레벨 {level}: {count}회")

    total_exit = result['Should_Exit'].sum()
    logger.info(f"실제 청산 필요: {total_exit}회")

    logger.debug("청산 신호 생성 완료")

    return result