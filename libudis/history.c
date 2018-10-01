/* History circular buffer */

#include <stdio.h>
#include <string.h>

#include "libudis.h"


history_entry_t *libudis_get_next_entry(emulator_history_t *history, int type) {
	history_entry_t *entry;
	if (history == NULL) {
		return NULL;
	}

	history->latest_entry_index = (history->latest_entry_index + 1) % history->num_allocated_entries;
	if ((history->latest_entry_index == history->first_entry_index) && (history->num_entries == history->num_allocated_entries)) {
		history->first_entry_index = (history->first_entry_index + 1) % history->num_allocated_entries;
	}
	if (history->num_entries < history->num_allocated_entries) {
		history->num_entries++;
	}
	history->cumulative_count++;
	entry = &history->entries[history->latest_entry_index];
	entry->disassembler_type = type;
	entry->num_bytes = 0;
	entry->flag = 0;
	return entry;
}
