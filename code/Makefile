
DATA_DIR = $(abspath ../data/)


extract-vq:
	python3 run_vq.py $(DATA_DIR)/acc $(DATA_DIR)/vq
	python3 check_csv_durs.py $(DATA_DIR)/acc $(DATA_DIR)/vq

find-vowels: extract-vq
	python3 find_vowels.py $(DATA_DIR)/vq $(DATA_DIR)/vowels/

build-chronograms:
	python3 build_chrono.py $(DATA_DIR)/spurts $(DATA_DIR)/beeps.csv $(DATA_DIR)/chrono/

get-features:
	python3 calculate_means.py $(DATA_DIR)/chrono $(DATA_DIR)/vq $(DATA_DIR)/vowels $(DATA_DIR)/features 0.05

run-analysis:
	Rscript -e 'rmarkdown::render("analyse.Rmd")'

all: run-analysis