"""
진입 신호 생성 모듈

이 모듈은 스테이지와 MACD 방향을 기반으로 매수/매도 진입 신호를 생성합니다.

Functions:
    generate_buy_signal: 매수 진입 신호 생성
    generate_sell_signal: 매도 진입 신호 생성
    check_entry_conditions: 진입 조건 상세 체크
    generate_entry_signals: 통합 진입 신호 생성
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def generate_buy_signal(
    data: pd.DataFrame,
    signal_type: str = 'normal'
) -> pd.DataFrame:
    """
    매수 진입 신호 생성
    
    Args:
        data: DataFrame (Stage, Dir_MACD_상, Dir_MACD_중, Dir_MACD_하, Close 필요)
        signal_type: 'normal' (통상 매수) 또는 'early' (조기 매수)
    
    Returns:
        pd.DataFrame: 신호 정보
            - Buy_Signal: 매수 신호 (0: 없음, 1: 통상, 2: 조기)
            - Signal_Reason: 신호 발생 이유
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없거나 signal_type이 잘못되었을 때
    
    Notes:
        통상 매수: 제6스테이지 + 3개 MACD 모두 우상향
        조기 매수: 제5스테이지 + 3개 MACD 모두 우상향 (리스크 높음)
    
    Examples:
        >>> df_with_signal = generate_buy_signal(df, 'normal')
        >>> buy_points = df_with_signal[df_with_signal['Buy_Signal'] > 0]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['Stage', 'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    if signal_type not in ['normal', 'early']:
        raise ValueError(f"signal_type은 'normal' 또는 'early'여야 합니다: {signal_type}")
    
    logger.debug(f"매수 신호 생성 시작: {signal_type}, {len(data)}개 데이터")
    
    # 결과 DataFrame 초기화
    result = pd.DataFrame(index=data.index)
    result['Buy_Signal'] = 0
    result['Signal_Reason'] = ''
    
    # 스테이지 조건
    if signal_type == 'normal':
        target_stage = 6
        signal_value = 1
        signal_name = '통상 매수'
    else:  # early
        target_stage = 5
        signal_value = 2
        signal_name = '조기 매수'
    
    stage_condition = (data['Stage'] == target_stage)
    
    # MACD 방향 조건 (3개 모두 우상향)
    macd_condition = (
        (data['Dir_MACD_상'] == 'up') &
        (data['Dir_MACD_중'] == 'up') &
        (data['Dir_MACD_하'] == 'up')
    )
    
    # 신호 생성
    signal_mask = stage_condition & macd_condition
    result.loc[signal_mask, 'Buy_Signal'] = signal_value
    result.loc[signal_mask, 'Signal_Reason'] = (
        f"{signal_name}: 제{target_stage}스테이지 + 3개 MACD 상승"
    )
    
    # 통계 로깅
    signal_count = signal_mask.sum()
    if signal_count > 0:
        logger.info(f"{signal_name} 신호 발생: {signal_count}회")
        # 평균 가격 로깅
        avg_price = data.loc[signal_mask, 'Close'].mean()
        logger.debug(f"신호 발생 평균 가격: {avg_price:,.0f}원")
    else:
        logger.debug(f"{signal_name} 신호 없음")
    
    logger.debug("매수 신호 생성 완료")
    
    return result


def generate_sell_signal(
    data: pd.DataFrame,
    signal_type: str = 'normal'
) -> pd.DataFrame:
    """
    매도 진입 신호 생성
    
    Args:
        data: DataFrame (Stage, Dir_MACD_상, Dir_MACD_중, Dir_MACD_하, Close 필요)
        signal_type: 'normal' (통상 매도) 또는 'early' (조기 매도)
    
    Returns:
        pd.DataFrame: 신호 정보
            - Sell_Signal: 매도 신호 (0: 없음, 1: 통상, 2: 조기)
            - Signal_Reason: 신호 발생 이유
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없거나 signal_type이 잘못되었을 때
    
    Notes:
        통상 매도: 제3스테이지 + 3개 MACD 모두 우하향
        조기 매도: 제2스테이지 + 3개 MACD 모두 우하향 (리스크 높음)
    
    Examples:
        >>> df_with_signal = generate_sell_signal(df, 'normal')
        >>> sell_points = df_with_signal[df_with_signal['Sell_Signal'] > 0]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['Stage', 'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    if signal_type not in ['normal', 'early']:
        raise ValueError(f"signal_type은 'normal' 또는 'early'여야 합니다: {signal_type}")
    
    logger.debug(f"매도 신호 생성 시작: {signal_type}, {len(data)}개 데이터")
    
    # 결과 DataFrame 초기화
    result = pd.DataFrame(index=data.index)
    result['Sell_Signal'] = 0
    result['Signal_Reason'] = ''
    
    # 스테이지 조건
    if signal_type == 'normal':
        target_stage = 3
        signal_value = 1
        signal_name = '통상 매도'
    else:  # early
        target_stage = 2
        signal_value = 2
        signal_name = '조기 매도'
    
    stage_condition = (data['Stage'] == target_stage)
    
    # MACD 방향 조건 (3개 모두 우하향)
    macd_condition = (
        (data['Dir_MACD_상'] == 'down') &
        (data['Dir_MACD_중'] == 'down') &
        (data['Dir_MACD_하'] == 'down')
    )
    
    # 신호 생성
    signal_mask = stage_condition & macd_condition
    result.loc[signal_mask, 'Sell_Signal'] = signal_value
    result.loc[signal_mask, 'Signal_Reason'] = (
        f"{signal_name}: 제{target_stage}스테이지 + 3개 MACD 하락"
    )
    
    # 통계 로깅
    signal_count = signal_mask.sum()
    if signal_count > 0:
        logger.info(f"{signal_name} 신호 발생: {signal_count}회")
        # 평균 가격 로깅
        avg_price = data.loc[signal_mask, 'Close'].mean()
        logger.debug(f"신호 발생 평균 가격: {avg_price:,.0f}원")
    else:
        logger.debug(f"{signal_name} 신호 없음")
    
    logger.debug("매도 신호 생성 완료")
    
    return result


def check_entry_conditions(
    data: pd.DataFrame,
    position_type: str
) -> Dict[str, Any]:
    """
    진입 조건 상세 체크
    
    Args:
        data: DataFrame (전체 지표 데이터)
        position_type: 'buy' 또는 'sell'
    
    Returns:
        Dict: 조건 체크 결과
            - stage_ok: 스테이지 조건 충족 여부 (bool)
            - macd_ok: MACD 조건 충족 여부 (bool)
            - all_ok: 모든 조건 충족 여부 (bool)
            - current_stage: 현재 스테이지 (int)
            - macd_directions: MACD 방향 (dict)
            - details: 상세 정보 (str)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: position_type이 잘못되었거나 필수 컬럼이 없을 때
    
    Examples:
        >>> conditions = check_entry_conditions(df.iloc[-1:], 'buy')
        >>> if conditions['all_ok']:
        ...     print("매수 진입 가능")
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if position_type not in ['buy', 'sell']:
        raise ValueError(f"position_type은 'buy' 또는 'sell'이어야 합니다: {position_type}")
    
    required_columns = ['Stage', 'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    if len(data) == 0:
        raise ValueError("데이터가 비어 있습니다")
    
    logger.debug(f"진입 조건 체크: {position_type}")
    
    # 최신 데이터 추출
    latest = data.iloc[-1]
    
    # 현재 상태
    current_stage = latest['Stage']
    macd_directions = {
        '상': latest['Dir_MACD_상'],
        '중': latest['Dir_MACD_중'],
        '하': latest['Dir_MACD_하']
    }
    
    # 조건 체크
    if position_type == 'buy':
        # 매수: 제5 또는 제6 스테이지
        stage_ok = current_stage in [5, 6]
        # MACD 모두 상승
        macd_ok = all(d == 'up' for d in macd_directions.values())
        
        if stage_ok and macd_ok:
            details = f"매수 조건 충족: 제{current_stage}스테이지, 3개 MACD 상승"
        elif not stage_ok:
            details = f"스테이지 미충족: 현재 제{current_stage}스테이지 (필요: 5 또는 6)"
        else:
            details = f"MACD 미충족: {macd_directions}"
    
    else:  # sell
        # 매도: 제2 또는 제3 스테이지
        stage_ok = current_stage in [2, 3]
        # MACD 모두 하락
        macd_ok = all(d == 'down' for d in macd_directions.values())
        
        if stage_ok and macd_ok:
            details = f"매도 조건 충족: 제{current_stage}스테이지, 3개 MACD 하락"
        elif not stage_ok:
            details = f"스테이지 미충족: 현재 제{current_stage}스테이지 (필요: 2 또는 3)"
        else:
            details = f"MACD 미충족: {macd_directions}"
    
    all_ok = stage_ok and macd_ok
    
    result = {
        'stage_ok': bool(stage_ok),
        'macd_ok': bool(macd_ok),
        'all_ok': bool(all_ok),
        'current_stage': int(current_stage) if not pd.isna(current_stage) else None,
        'macd_directions': macd_directions,
        'details': details
    }
    
    logger.debug(f"조건 체크 결과: {result['details']}")
    
    return result


def generate_entry_signals(
    data: pd.DataFrame,
    enable_early: bool = False
) -> pd.DataFrame:
    """
    통합 진입 신호 생성 (매수 + 매도)
    
    Args:
        data: DataFrame (전체 지표 데이터)
        enable_early: 조기 진입 신호 활성화 여부
    
    Returns:
        pd.DataFrame: 통합 신호
            - Entry_Signal: 진입 신호 
                (-2: 조기매도, -1: 통상매도, 0: 없음, 1: 통상매수, 2: 조기매수)
            - Signal_Type: 신호 타입 ('buy', 'sell', None)
            - Signal_Reason: 신호 발생 이유
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Notes:
        enable_early=False일 때는 통상 신호만 생성
        enable_early=True일 때는 통상 + 조기 신호 생성
    
    Examples:
        >>> signals = generate_entry_signals(df, enable_early=False)
        >>> buy_signals = signals[signals['Entry_Signal'] > 0]
        >>> sell_signals = signals[signals['Entry_Signal'] < 0]
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['Stage', 'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"통합 진입 신호 생성 시작: enable_early={enable_early}, {len(data)}개 데이터")
    
    # 결과 DataFrame 초기화
    result = pd.DataFrame(index=data.index)
    result['Entry_Signal'] = 0
    result['Signal_Type'] = None
    result['Signal_Reason'] = ''
    
    # 통상 매수 신호
    normal_buy = generate_buy_signal(data, 'normal')
    buy_mask = normal_buy['Buy_Signal'] > 0
    result.loc[buy_mask, 'Entry_Signal'] = 1
    result.loc[buy_mask, 'Signal_Type'] = 'buy'
    result.loc[buy_mask, 'Signal_Reason'] = normal_buy.loc[buy_mask, 'Signal_Reason']
    
    # 통상 매도 신호
    normal_sell = generate_sell_signal(data, 'normal')
    sell_mask = normal_sell['Sell_Signal'] > 0
    result.loc[sell_mask, 'Entry_Signal'] = -1
    result.loc[sell_mask, 'Signal_Type'] = 'sell'
    result.loc[sell_mask, 'Signal_Reason'] = normal_sell.loc[sell_mask, 'Signal_Reason']
    
    # 조기 신호 (옵션)
    if enable_early:
        # 조기 매수 신호
        early_buy = generate_buy_signal(data, 'early')
        early_buy_mask = early_buy['Buy_Signal'] > 0
        # 통상 신호가 없는 곳에만 조기 신호 적용
        early_buy_only = early_buy_mask & (result['Entry_Signal'] == 0)
        result.loc[early_buy_only, 'Entry_Signal'] = 2
        result.loc[early_buy_only, 'Signal_Type'] = 'buy'
        result.loc[early_buy_only, 'Signal_Reason'] = early_buy.loc[early_buy_only, 'Signal_Reason']
        
        # 조기 매도 신호
        early_sell = generate_sell_signal(data, 'early')
        early_sell_mask = early_sell['Sell_Signal'] > 0
        # 통상 신호가 없는 곳에만 조기 신호 적용
        early_sell_only = early_sell_mask & (result['Entry_Signal'] == 0)
        result.loc[early_sell_only, 'Entry_Signal'] = -2
        result.loc[early_sell_only, 'Signal_Type'] = 'sell'
        result.loc[early_sell_only, 'Signal_Reason'] = early_sell.loc[early_sell_only, 'Signal_Reason']
    
    # 통계 로깅 (신호가 있을 때만 출력)
    buy_count = (result['Entry_Signal'] > 0).sum()
    sell_count = (result['Entry_Signal'] < 0).sum()

    if buy_count > 0 or sell_count > 0:
        logger.info(f"진입 신호 생성 완료: 매수 {buy_count}회, 매도 {sell_count}회")

    if enable_early:
        normal_buy_count = (result['Entry_Signal'] == 1).sum()
        early_buy_count = (result['Entry_Signal'] == 2).sum()
        normal_sell_count = (result['Entry_Signal'] == -1).sum()
        early_sell_count = (result['Entry_Signal'] == -2).sum()
        logger.debug(
            f"상세: 통상매수 {normal_buy_count}, 조기매수 {early_buy_count}, "
            f"통상매도 {normal_sell_count}, 조기매도 {early_sell_count}"
        )

    logger.debug("통합 진입 신호 생성 완료")
    
    return result
