from typing import Tuple
from app.models import Match, Prediction


def calculate_points(match: Match, prediction: Prediction) -> Tuple[int, int, int, int, int]:
    """
    Calculate points based on the prediction logic:
    - Acertar vencedor/empate: +2 pontos
    - Acertar gols Time A: +2 pontos  
    - Acertar gols Time B: +2 pontos
    - Bônus placar exato: +2 pontos
    
    Returns: (total, winner_points, score_a_points, score_b_points, exact_points)
    """
    if match.score_a is None or match.score_b is None:
        return 0, 0, 0, 0, 0
    
    pred_a = prediction.predicted_score_a
    pred_b = prediction.predicted_score_b
    actual_a = match.score_a
    actual_b = match.score_b
    
    points_winner = 0
    points_score_a = 0
    points_score_b = 0
    points_exact = 0
    
    # Check winner/draw
    pred_result = 0  # 0 = draw, 1 = A wins, 2 = B wins
    actual_result = 0
    
    if pred_a > pred_b:
        pred_result = 1
    elif pred_b > pred_a:
        pred_result = 2
    
    if actual_a > actual_b:
        actual_result = 1
    elif actual_b > actual_a:
        actual_result = 2
    
    # Winner/draw points
    if pred_result == actual_result:
        points_winner = 2
    
    # Score A points
    if pred_a == actual_a:
        points_score_a = 2
    
    # Score B points
    if pred_b == actual_b:
        points_score_b = 2
    
    # Exact score bonus
    if pred_a == actual_a and pred_b == actual_b:
        points_exact = 2
    
    total = points_winner + points_score_a + points_score_b + points_exact
    
    return total, points_winner, points_score_a, points_score_b, points_exact


def get_points_breakdown(match: Match, prediction: Prediction) -> dict:
    """Get detailed points breakdown for display"""
    total, winner, score_a, score_b, exact = calculate_points(match, prediction)
    
    return {
        "total": total,
        "winner": winner,
        "score_a": score_a,
        "score_b": score_b,
        "exact": exact,
        "breakdown": {
            "acertou_resultado": winner > 0,
            "acertou_gols_time_a": score_a > 0,
            "acertou_gols_time_b": score_b > 0,
            "acertou_placar_exato": exact > 0
        }
    }


def calculate_prediction_score(match: Match, prediction: Prediction) -> int:
    """Simple function to get total points only"""
    total, _, _, _, _ = calculate_points(match, prediction)
    return total
