def find_relationship(source_entity, target_entity):
    if (
        source_entity == "Person A"
        and target_entity == "Account XYZ234"
    ):
        return {
            "found": True,
            "path": [
                "Person A",
                "Person B",
                "Account XYZ234"
            ],
            "relationships": [
                {
                    "from": "Person A",
                    "relation": "ASSOCIATED_WITH",
                    "to": "Person B",
                    "evidence": "SURV-001",
                    "date": "2026-08-15 11:15:00"
                },
                {
                    "from": "Person B",
                    "relation": "TRANSACTION",
                    "to": "Account XYZ234",
                    "evidence": "FIN-001",
                    "date": "2026-08-15 12:03:21",
                    "amount": 200000
                }
            ]
        }

    return {
        "found": False,
        "path": [],
        "relationships": []
    }