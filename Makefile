.PHONY: init

init:
	mkdir -p $(NAME) $(NAME)/tests
	touch $(NAME)/__init__.py
	touch $(NAME)/tests/.gitkeep
	cd $(NAME) && poetry init