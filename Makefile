.PHONY: reproduce-offline reproduce-offline-no-tex paper-assets check-paper-consistency

reproduce-offline:
	bash scripts/reproduce_offline_artifact.sh

reproduce-offline-no-tex:
	bash scripts/reproduce_offline_artifact.sh --skip-manuscript

paper-assets:
	bash scripts/generate_paper_assets.sh

check-paper-consistency:
	python3 tools/consistency_check.py
