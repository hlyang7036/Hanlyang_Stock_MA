"""
신호 강도 평가 모듈

이 모듈은 진입/청산 신호의 품질을 0-100점으로 수치화합니다.

Functions:
    evaluate_signal_strength: 신호 강도 종합 평가 (메인 함수)
    calculate_macd_alignment_score: MACD 방향 일치도 점수 계산
    calculate_trend_strength_score: 추세 강도 점수 계산
    calculate_momentum_score: 모멘텀 점수 계산
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

# 상위 모듈에서 필요한 함수 임포트
from ..stage import calculate_ma_spread, check_ma_slope

logger = logging.getLogger(__name__)


def calculate_macd_alignment_score(data: pd.DataFrame) -> pd.Series:
    """
    MACD 3종 방향 일치도 점수 계산 (0-30점)
    
    3개의 MACD(상/중/하)가 같은 방향으로 정렬되어 있을수록 높은 점수를 부여합니다.
    방향 일치도는 강한 추세 신호의 핵심 지표입니다.
    
    Args:
        data: DataFrame (Dir_MACD_상, Dir_MACD_중, Dir_MACD_하 컬럼 필요)
    
    Returns:
        pd.Series: MACD 일치도 점수 (0-30점)
            - 30점: 3개 모두 같은 방향 (강한 추세)
            - 20점: 2개 일치
            - 10점: 1개만 특정 방향
            - 0점: 모두 neutral 또는 데이터 부족
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> df['Alignment_Score'] = calculate_macd_alignment_score(df)
        >>> strong_signals = df[df['Alignment_Score'] == 30]  # 완벽한 일치
    
    Notes:
        - 'up', 'down', 'neutral' 값을 가정
        - neutral은 방향성 없음으로 간주
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"MACD 일치도 점수 계산 시작: {len(data)}개 데이터")
    
    # 방향별 카운트
    up_count = (
        (data['Dir_MACD_상'] == 'up').astype(int) +
        (data['Dir_MACD_중'] == 'up').astype(int) +
        (data['Dir_MACD_하'] == 'up').astype(int)
    )
    
    down_count = (
        (data['Dir_MACD_상'] == 'down').astype(int) +
        (data['Dir_MACD_중'] == 'down').astype(int) +
        (data['Dir_MACD_하'] == 'down').astype(int)
    )
    
    # 점수 계산
    score = pd.Series(0, index=data.index, dtype=int)
    
    # 3개 모두 일치: 30점 (가장 강한 신호)
    score[(up_count == 3) | (down_count == 3)] = 30
    
    # 2개 일치: 20점 (아직 점수가 0인 행만)
    score[((up_count == 2) | (down_count == 2)) & (score == 0)] = 20
    
    # 1개만 방향성: 10점 (아직 점수가 0인 행만)
    score[((up_count == 1) | (down_count == 1)) & (score == 0)] = 10
    
    # 통계 로깅
    perfect_count = ((up_count == 3) | (down_count == 3)).sum()
    if len(data) > 0:
        logger.info(f"MACD 완벽 일치: {perfect_count}회 ({perfect_count/len(data)*100:.1f}%)")
    
    return score


def calculate_trend_strength_score(data: pd.DataFrame) -> pd.Series:
    """
    추세 강도 점수 계산 (0-40점)
    
    이동평균선 배열 상태와 간격을 평가하여 추세의 강도를 측정합니다.
    
    평가 항목:
    - 이동평균선 배열 (Stage): 0-20점
    - 이동평균선 간격 (Spread): 0-20점
    
    Args:
        data: DataFrame (Stage, EMA_5, EMA_20, EMA_40, Close 컬럼 필요)
    
    Returns:
        pd.Series: 추세 강도 점수 (0-40점)
            - 40점: 완벽한 배열 + 넓은 간격 (강한 추세)
            - 20-39점: 양호한 추세
            - 10-19점: 약한 추세
            - 0-9점: 추세 없음
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> df['Trend_Score'] = calculate_trend_strength_score(df)
        >>> strong_trends = df[df['Trend_Score'] >= 30]
    
    Notes:
        - Stage 6 (완벽한 상승): 20점
        - Stage 3 (완벽한 하락): 20점
        - 간격은 Close 대비 백분율로 정규화
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['Stage', 'EMA_5', 'EMA_20', 'EMA_40', 'Close']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"추세 강도 점수 계산 시작: {len(data)}개 데이터")
    
    # A. 이동평균선 배열 점수 (0-20점)
    arrangement_score = pd.Series(0, index=data.index, dtype=int)
    
    # 강세 배열
    arrangement_score[data['Stage'] == 6] = 20  # 완벽한 상승 배열
    arrangement_score[data['Stage'] == 5] = 15  # 상승 배열 진입
    
    # 약세 배열
    arrangement_score[data['Stage'] == 3] = 20  # 완벽한 하락 배열
    arrangement_score[data['Stage'] == 2] = 15  # 하락 배열 진입
    
    # 혼조
    arrangement_score[data['Stage'].isin([1, 4])] = 5  # 불명확한 배열
    
    # B. 이동평균선 간격 점수 (0-20점)
    spread_score = pd.Series(0, index=data.index, dtype=int)
    
    try:
        # calculate_ma_spread 함수 활용
        spread_df = calculate_ma_spread(data)
        
        # 간격을 Close 대비 백분율로 정규화
        spread_5_20 = spread_df['Spread_5_20'].abs() / data['Close'] * 100
        spread_20_40 = spread_df['Spread_20_40'].abs() / data['Close'] * 100
        
        # 총 간격
        total_spread = spread_5_20 + spread_20_40
        
        # 백분위수 기반 점수화 (간격이 넓을수록 강한 추세)
        threshold_80 = total_spread.quantile(0.8)
        threshold_60 = total_spread.quantile(0.6)
        threshold_40 = total_spread.quantile(0.4)
        
        spread_score[total_spread >= threshold_80] = 20  # 상위 20%
        spread_score[(total_spread >= threshold_60) & (total_spread < threshold_80)] = 15
        spread_score[(total_spread >= threshold_40) & (total_spread < threshold_60)] = 10
        spread_score[total_spread < threshold_40] = 5
        
    except Exception as e:
        logger.warning(f"간격 점수 계산 중 오류 (기본값 5점 적용): {e}")
        spread_score[:] = 5
    
    # 최종 점수
    total_score = arrangement_score + spread_score
    
    # 통계 로깅
    high_score_count = (total_score >= 30).sum()
    if len(data) > 0:
        logger.info(f"강한 추세 (30점 이상): {high_score_count}회 ({high_score_count/len(data)*100:.1f}%)")
    
    return total_score


def calculate_momentum_score(data: pd.DataFrame, slope_period: int = 5) -> pd.Series:
    """
    모멘텀 점수 계산 (0-30점)
    
    이동평균선 기울기와 변동성(ATR)을 평가하여 모멘텀 강도를 측정합니다.
    
    평가 항목:
    - 이동평균선 기울기 (EMA_40): 0-20점
    - ATR 변동성: 0-10점
    
    Args:
        data: DataFrame (EMA_40, ATR 컬럼 필요)
        slope_period: 기울기 계산 기간 (기본값: 5)
    
    Returns:
        pd.Series: 모멘텀 점수 (0-30점)
            - 30점: 강한 기울기 + 적정 변동성
            - 20-29점: 양호한 모멘텀
            - 10-19점: 약한 모멘텀
            - 0-9점: 모멘텀 없음
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없을 때
    
    Examples:
        >>> df['Momentum_Score'] = calculate_momentum_score(df)
        >>> high_momentum = df[df['Momentum_Score'] >= 25]
    
    Notes:
        - 기울기는 장기선(EMA_40) 중심으로 평가
        - ATR은 너무 낮거나 높으면 감점 (적정 범위 선호)
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    required_columns = ['EMA_5', 'EMA_20', 'EMA_40', 'ATR']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    logger.debug(f"모멘텀 점수 계산 시작: {len(data)}개 데이터")
    
    # A. 이동평균선 기울기 점수 (0-20점)
    slope_score = pd.Series(0, index=data.index, dtype=int)
    
    try:
        # check_ma_slope 함수 활용
        slope_result = check_ma_slope(data, period=slope_period)
        
        # EMA_40 (장기선) 기울기 중심 평가
        slope_score[slope_result['Slope_EMA_40'] == 'strong_up'] = 20
        slope_score[slope_result['Slope_EMA_40'] == 'strong_down'] = 20
        
        slope_score[slope_result['Slope_EMA_40'] == 'up'] = 15
        slope_score[slope_result['Slope_EMA_40'] == 'down'] = 15
        
        slope_score[slope_result['Slope_EMA_40'] == 'weak_up'] = 10
        slope_score[slope_result['Slope_EMA_40'] == 'weak_down'] = 10
        
        slope_score[slope_result['Slope_EMA_40'] == 'flat'] = 0
        
    except Exception as e:
        logger.warning(f"기울기 점수 계산 중 오류 (기본값 5점 적용): {e}")
        slope_score[:] = 5
    
    # B. ATR 변동성 점수 (0-10점)
    volatility_score = pd.Series(0, index=data.index, dtype=int)
    
    try:
        # ATR 백분위수 계산
        atr_percentile = data['ATR'].rank(pct=True) * 100
        
        # 적정 변동성 범위 (40-70 백분위): 가장 높은 점수
        volatility_score[(atr_percentile >= 40) & (atr_percentile <= 70)] = 10
        
        # 약간 높거나 낮음 (20-40, 70-85): 중간 점수
        volatility_score[
            ((atr_percentile >= 20) & (atr_percentile < 40)) |
            ((atr_percentile > 70) & (atr_percentile <= 85))
        ] = 7
        
        # 너무 낮거나 높음 (<20, >85): 낮은 점수
        volatility_score[(atr_percentile < 20) | (atr_percentile > 85)] = 3
        
    except Exception as e:
        logger.warning(f"변동성 점수 계산 중 오류 (기본값 5점 적용): {e}")
        volatility_score[:] = 5
    
    # 최종 점수
    total_score = slope_score + volatility_score
    
    # 통계 로깅
    high_score_count = (total_score >= 25).sum()
    if len(data) > 0:
        logger.info(f"강한 모멘텀 (25점 이상): {high_score_count}회 ({high_score_count/len(data)*100:.1f}%)")
    
    return total_score


def evaluate_signal_strength(
    data: pd.DataFrame,
    signal_type: str = 'entry',
    slope_period: int = 5
) -> pd.Series:
    """
    신호 강도 종합 평가 (0-100점)
    
    MACD 일치도, 추세 강도, 모멘텀을 종합하여 신호의 품질을 수치화합니다.
    
    평가 항목:
    - MACD 방향 일치도: 30점
    - 추세 강도 (배열 + 간격): 40점
    - 모멘텀 (기울기 + 변동성): 30점
    
    Args:
        data: DataFrame (전체 지표 데이터 필요)
        signal_type: 신호 유형 ('entry' 또는 'exit')
        slope_period: 기울기 계산 기간 (기본값: 5)
    
    Returns:
        pd.Series: 신호 강도 점수 (0-100점)
            - 90-100점: 매우 강한 신호 (최우선 진입)
            - 70-89점: 강한 신호 (진입 고려)
            - 50-69점: 보통 신호 (신중한 진입)
            - 30-49점: 약한 신호 (대기 권장)
            - 0-29점: 매우 약한 신호 (진입 회피)
    
    Raises:
        TypeError: data가 DataFrame이 아닐 때
        ValueError: 필수 컬럼이 없거나 signal_type이 잘못되었을 때
    
    Examples:
        >>> df['Signal_Strength'] = evaluate_signal_strength(df, 'entry')
        >>> strong_signals = df[df['Signal_Strength'] >= 70]
        >>> strong_signals.describe()
    
    Notes:
        - 모든 하위 점수는 독립적으로 계산됨
        - 결과는 자동으로 0-100 범위로 제한됨
        - signal_type은 현재 버전에서는 로깅 용도로만 사용
    """
    # 입력 검증
    if not isinstance(data, pd.DataFrame):
        raise TypeError(f"DataFrame이 필요합니다. 입력 타입: {type(data)}")
    
    if signal_type not in ['entry', 'exit']:
        raise ValueError(f"signal_type은 'entry' 또는 'exit'여야 합니다: {signal_type}")
    
    logger.info(f"신호 강도 평가 시작: {signal_type}, {len(data)}개 데이터")
    
    # 필수 컬럼 체크
    required_columns = [
        'Dir_MACD_상', 'Dir_MACD_중', 'Dir_MACD_하',
        'Stage', 'EMA_5', 'EMA_20', 'EMA_40', 'ATR', 'Close'
    ]
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"필수 컬럼이 없습니다: {missing_columns}")
    
    try:
        # 1. MACD 일치도 점수 (0-30점)
        macd_score = calculate_macd_alignment_score(data)
        logger.debug(f"MACD 점수 평균: {macd_score.mean():.1f}점")
        
        # 2. 추세 강도 점수 (0-40점)
        trend_score = calculate_trend_strength_score(data)
        logger.debug(f"추세 점수 평균: {trend_score.mean():.1f}점")
        
        # 3. 모멘텀 점수 (0-30점)
        momentum_score = calculate_momentum_score(data, slope_period=slope_period)
        logger.debug(f"모멘텀 점수 평균: {momentum_score.mean():.1f}점")
        
        # 4. 총점 계산
        total_score = macd_score + trend_score + momentum_score
        
        # 범위 제한 (0-100)
        total_score = total_score.clip(0, 100)
        
        # 통계 로깅
        logger.info(f"신호 강도 평가 완료:")
        logger.info(f"  - 평균: {total_score.mean():.1f}점")
        logger.info(f"  - 중앙값: {total_score.median():.1f}점")
        logger.info(f"  - 최대: {total_score.max()}점")
        logger.info(f"  - 최소: {total_score.min()}점")
        
        # 등급별 분포
        very_strong = (total_score >= 90).sum()
        strong = ((total_score >= 70) & (total_score < 90)).sum()
        normal = ((total_score >= 50) & (total_score < 70)).sum()
        weak = ((total_score >= 30) & (total_score < 50)).sum()
        very_weak = (total_score < 30).sum()
        
        if len(data) > 0:
            logger.info(f"  - 매우 강함(90+): {very_strong}회 ({very_strong/len(data)*100:.1f}%)")
            logger.info(f"  - 강함(70-89): {strong}회 ({strong/len(data)*100:.1f}%)")
            logger.info(f"  - 보통(50-69): {normal}회 ({normal/len(data)*100:.1f}%)")
            logger.info(f"  - 약함(30-49): {weak}회 ({weak/len(data)*100:.1f}%)")
            logger.info(f"  - 매우 약함(0-29): {very_weak}회 ({very_weak/len(data)*100:.1f}%)")
        
        return total_score
        
    except Exception as e:
        logger.error(f"신호 강도 평가 중 오류 발생: {e}")
        raise
