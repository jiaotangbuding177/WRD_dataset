#!/bin/bash
SKILL=…kill
IN=/workspace/outputs/reproduction_inputs
OUT=/workspace/tmp/replay_run
LOG=/workspace/outputs/making_history
rm -rf $OUT && mkdir -p $OUT

echo "### case: normal" > $LOG/normal.log
echo "## command: python $SKILL/scripts/apply_minutes_format.py $IN/meeting_minutes.docx --out $OUT/minutes_formatted.docx --report $OUT/format_summary.json --remove-stars" >> $LOG/normal.log
python $SKILL/scripts/apply_minutes_format.py $IN/meeting_minutes.docx --out $OUT/minutes_formatted.docx --report $OUT/format_summary.json --remove-stars > $OUT/normal.stdout 2> $OUT/normal.stderr
echo "## exit: $?" >> $LOG/normal.log
echo "## stdout:" >> $LOG/normal.log; cat $OUT/normal.stdout >> $LOG/normal.log
echo "## stderr:" >> $LOG/normal.log; cat $OUT/normal.stderr >> $LOG/normal.log

echo "### case: boundary" > $LOG/boundary.log
echo "## command: python $SKILL/scripts/apply_minutes_format.py $IN/boundary_meeting_minutes.docx --out $OUT/boundary_formatted.docx --report $OUT/boundary_summary.json" >> $LOG/boundary.log
python $SKILL/scripts/apply_minutes_format.py $IN/boundary_meeting_minutes.docx --out $OUT/boundary_formatted.docx --report $OUT/boundary_summary.json > $OUT/boundary.stdout 2> $OUT/boundary.stderr
echo "## exit: $?" >> $LOG/boundary.log
echo "## stdout:" >> $LOG/boundary.log; cat $OUT/boundary.stdout >> $LOG/boundary.log
echo "## stderr:" >> $LOG/boundary.log; cat $OUT/boundary.stderr >> $LOG/boundary.log

echo "### case: invalid_input" > $LOG/invalid_input.log
echo "## command: python $SKILL/scripts/apply_minutes_format.py $IN/invalid_input.docx --out $OUT/should_not_exist.docx" >> $LOG/invalid_input.log
python $SKILL/scripts/apply_minutes_format.py $IN/invalid_input.docx --out $OUT/should_not_exist.docx > $OUT/invalid.stdout 2> $OUT/invalid.stderr
echo "## exit: $?" >> $LOG/invalid_input.log
echo "## stdout:" >> $LOG/invalid_input.log; cat $OUT/invalid.stdout >> $LOG/invalid_input.log
echo "## stderr:" >> $LOG/invalid_input.log; cat $OUT/invalid.stderr >> $LOG/invalid_input.log
if [ -f $OUT/should_not_exist.docx ]; then echo "## output file: EXISTS (unexpected)" >> $LOG/invalid_input.log; else echo "## output file: not created (expected)" >> $LOG/invalid_input.log; fi

echo "### case: composition_two_pass" > $LOG/composition_two_pass.log
echo "## command1: python $SKILL/scripts/apply_minutes_format.py $IN/meeting_minutes.docx --out $OUT/step1_kaiti.docx --report $OUT/step1_summary.json --remove-stars" >> $LOG/composition_two_pass.log
python $SKILL/scripts/apply_minutes_format.py $IN/meeting_minutes.docx --out $OUT/step1_kaiti.docx --report $OUT/step1_summary.json --remove-stars > $OUT/comp1.stdout 2> $OUT/comp1.stderr
echo "## exit1: $?" >> $LOG/composition_two_pass.log
echo "## stdout1:" >> $LOG/composition_two_pass.log; cat $OUT/comp1.stdout >> $LOG/composition_two_pass.log
echo "## stderr1:" >> $LOG/composition_two_pass.log; cat $OUT/comp1.stderr >> $LOG/composition_two_pass.log
echo "## command2: python $SKILL/scripts/apply_minutes_format.py $OUT/step1_kaiti.docx --out $OUT/step2_songti.docx --cn-font 宋体 --report $OUT/step2_summary.json" >> $LOG/composition_two_pass.log
python $SKILL/scripts/apply_minutes_format.py $OUT/step1_kaiti.docx --out $OUT/step2_songti.docx --cn-font 宋体 --report $OUT/step2_summary.json > $OUT/comp2.stdout 2> $OUT/comp2.stderr
echo "## exit2: $?" >> $LOG/composition_two_pass.log
echo "## stdout2:" >> $LOG/composition_two_pass.log; cat $OUT/comp2.stdout >> $LOG/composition_two_pass.log
echo "## stderr2:" >> $LOG/composition_two_pass.log; cat $OUT/comp2.stderr >> $LOG/composition_two_pass.log

echo "=== all runs done ==="
cat $OUT/format_summary.json
