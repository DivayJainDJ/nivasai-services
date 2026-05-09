"""Test complete housing matching flow end-to-end."""

import pytest
from unittest.mock import MagicMock, patch


class TestHousingFlow:
    """Test complete housing workflow."""
    
    def test_housing_match_end_to_end(
        self,
        client,
        mock_firestore,
        mock_gemini,
        mock_gemini_response,
        sample_housing_request,
        sample_housing_unit,
    ):
        """Test housing matching from request to recommendations."""
        # Mock housing units in Firestore
        mock_units = []
        for i in range(5):
            mock_doc = MagicMock()
            unit = sample_housing_unit.copy()
            unit["unitId"] = f"H00{i+1}"
            unit["rent"] = 12000 + (i * 1000)
            mock_doc.to_dict.return_value = unit
            mock_units.append(mock_doc)
        
        mock_firestore.collection.return_value.where.return_value.where.return_value.stream.return_value = mock_units
        
        # Mock Google Maps API
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                "rows": [{
                    "elements": [{
                        "distance": {"value": 2300, "text": "2.3 km"},
                        "duration": {"value": 600, "text": "10 mins"},
                        "status": "OK"
                    }]
                }],
                "status": "OK"
            }
            
            # Mock Gemini explanation
            explanation_response = mock_gemini_response(
                "This 2BHK unit is perfect for your family of 4. It's close to your location and within your budget."
            )
            
            with patch('app.housing_matcher.explanation_generator.get_gemini_client') as mock_gemini_client:
                mock_model = MagicMock()
                mock_model.generate_content.return_value = explanation_response
                mock_gemini_client.return_value.GenerativeModel.return_value = mock_model
                
                # Request housing match
                response = client.post("/api/housing/match", json=sample_housing_request)
                
                assert response.status_code == 200
                data = response.json()
                assert "recommendations" in data
                assert len(data["recommendations"]) <= 3
                
                # Verify recommendations have required fields
                for rec in data["recommendations"]:
                    assert "unitId" in rec
                    assert "name" in rec
                    assert "distance_km" in rec
                    assert "explanation" in rec
    
    def test_eligibility_filtering(
        self,
        mock_firestore,
        sample_housing_unit,
    ):
        """Test eligibility filtering works correctly."""
        from app.housing_matcher.eligibility_engine import EligibilityEngine
        
        engine = EligibilityEngine()
        
        # Test EWS eligibility (income < 25000)
        eligibility = engine.determine_eligibility(20000, 4)
        assert eligibility == "EWS"
        
        # Test LIG eligibility (income 25000-50000)
        eligibility = engine.determine_eligibility(35000, 4)
        assert eligibility == "LIG"
        
        # Test MIG eligibility (income 50000-100000)
        eligibility = engine.determine_eligibility(75000, 4)
        assert eligibility == "MIG"
        
        # Test unit filtering
        unit = sample_housing_unit.copy()
        unit["eligibility"] = "EWS"
        
        is_eligible = engine.check_unit_eligibility(unit, "EWS", 4)
        assert is_eligible is True
        
        is_eligible = engine.check_unit_eligibility(unit, "LIG", 4)
        assert is_eligible is False
    
    def test_distance_scoring(
        self,
        sample_housing_unit,
    ):
        """Test distance scoring with Google Maps API."""
        from app.housing_matcher.distance_scorer import DistanceScorer
        
        scorer = DistanceScorer()
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                "rows": [{
                    "elements": [{
                        "distance": {"value": 5000, "text": "5.0 km"},
                        "duration": {"value": 900, "text": "15 mins"},
                        "status": "OK"
                    }]
                }],
                "status": "OK"
            }
            
            distance_km = scorer.calculate_distance(
                "Andheri West",
                sample_housing_unit["coordinates"]
            )
            
            assert distance_km is not None
            assert distance_km > 0
    
    def test_ranking_engine(
        self,
        sample_housing_unit,
    ):
        """Test ranking engine prioritizes correctly."""
        from app.housing_matcher.ranking_engine import RankingEngine
        
        engine = RankingEngine()
        
        # Create multiple units with different distances
        units = []
        for i in range(5):
            unit = sample_housing_unit.copy()
            unit["unitId"] = f"H00{i+1}"
            unit["distance_km"] = float(i + 1)
            unit["rent"] = 12000 + (i * 1000)
            units.append(unit)
        
        # Rank units
        ranked = engine.rank_units(units, "EWS", 25000)
        
        assert len(ranked) <= 3
        # Closest unit should be ranked first
        assert ranked[0]["distance_km"] <= ranked[-1]["distance_km"]
