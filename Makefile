.PHONY: init

init:
	mkdir -p $(NAME) $(NAME)/(NAME) $(NAME)/tests
	touch $(NAME)/(NAME)/__init__.py
	touch $(NAME)/tests/.gitkeep
	cd $(NAME) && poetry init