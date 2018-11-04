/* History circular buffer */

#include <stdio.h>
#include <string.h>

#include "libudis.h"

char opcode_history_flags_6502[256] = {
    0, /* BRK impl */
    FLAG_MEMORY_READ_ALTER_A, /* ORA X,ind */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ORA zpg */
    FLAG_MEMORY_ALTER, /* ASL zpg */
    0, /* ??? */
    FLAG_PUSH_SR, /* PHP impl */
    0, /* ORA # */
    0, /* ASL A */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ORA abs */
    FLAG_MEMORY_ALTER, /* ASL abs */
    0, /* ??? */
    0, /* BPL rel */
    FLAG_MEMORY_READ_ALTER_A, /* ORA ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ORA zpg,X */
    FLAG_MEMORY_ALTER, /* ASL zpg,X */
    0, /* ??? */
    0, /* CLC impl */
    FLAG_MEMORY_READ_ALTER_A, /* ORA abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ORA abs,X */
    FLAG_MEMORY_ALTER, /* ASL abs,X */
    0, /* ??? */
    0, /* JSR abs */
    FLAG_MEMORY_READ_ALTER_A, /* AND X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* BIT zpg */
    FLAG_MEMORY_READ_ALTER_A, /* AND zpg */
    FLAG_MEMORY_ALTER, /* ROL zpg */
    0, /* ??? */
    FLAG_PULL_SR, /* PLP impl */
    0, /* AND # */
    0, /* ROL A */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* BIT abs */
    FLAG_MEMORY_READ_ALTER_A, /* AND abs */
    FLAG_MEMORY_ALTER, /* ROL abs */
    0, /* ??? */
    0, /* BMI rel */
    FLAG_MEMORY_READ_ALTER_A, /* AND ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* AND zpg,X */
    FLAG_MEMORY_ALTER, /* ROL zpg,X */
    0, /* ??? */
    0, /* SEC impl */
    FLAG_MEMORY_READ_ALTER_A, /* AND abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* AND abs,X */
    FLAG_MEMORY_ALTER, /* ROL abs,X */
    0, /* ??? */
    FLAG_RTI, /* RTI impl */
    FLAG_MEMORY_READ_ALTER_A, /* EOR X,ind */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* EOR zpg */
    FLAG_MEMORY_ALTER, /* LSR zpg */
    0, /* ??? */
    FLAG_PUSH_A, /* PHA impl */
    0, /* EOR # */
    0, /* LSR A */
    0, /* ??? */
    0, /* JMP abs */
    FLAG_MEMORY_READ_ALTER_A, /* EOR abs */
    FLAG_MEMORY_ALTER, /* LSR abs */
    0, /* ??? */
    0, /* BVC rel */
    FLAG_MEMORY_READ_ALTER_A, /* EOR ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* EOR zpg,X */
    FLAG_MEMORY_ALTER, /* LSR zpg,X */
    0, /* ??? */
    0, /* CLI impl */
    FLAG_MEMORY_READ_ALTER_A, /* EOR abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* EOR abs,X */
    FLAG_MEMORY_ALTER, /* LSR abs,X */
    0, /* ??? */
    FLAG_RTS, /* RTS impl */
    FLAG_MEMORY_READ_ALTER_A, /* ADC X,ind */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ADC zpg */
    FLAG_MEMORY_ALTER, /* ROR zpg */
    0, /* ??? */
    FLAG_PULL_A, /* PLA impl */
    0, /* ADC # */
    0, /* ROR A */
    0, /* ??? */
    0, /* JMP ind */
    FLAG_MEMORY_READ_ALTER_A, /* ADC abs */
    FLAG_MEMORY_ALTER, /* ROR abs */
    0, /* ??? */
    0, /* BVS rel */
    FLAG_MEMORY_READ_ALTER_A, /* ADC ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ADC zpg,X */
    FLAG_MEMORY_ALTER, /* ROR zpg,X */
    0, /* ??? */
    0, /* SEI impl */
    FLAG_MEMORY_READ_ALTER_A, /* ADC abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* ADC abs,X */
    FLAG_MEMORY_ALTER, /* ROR abs,X */
    0, /* ??? */
    0, /* ??? */
    FLAG_STORE_A_IN_MEMORY, /* STA X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_STORE_Y_IN_MEMORY, /* STY zpg */
    FLAG_STORE_A_IN_MEMORY, /* STA zpg */
    FLAG_STORE_X_IN_MEMORY, /* STX zpg */
    0, /* ??? */
    0, /* DEY impl */
    0, /* ??? */
    0, /* TXA impl */
    0, /* ??? */
    FLAG_STORE_Y_IN_MEMORY, /* STY abs */
    FLAG_STORE_A_IN_MEMORY, /* STA abs */
    FLAG_STORE_X_IN_MEMORY, /* STX abs */
    0, /* ??? */
    0, /* BCC rel */
    FLAG_STORE_A_IN_MEMORY, /* STA ind,Y */
    0, /* ??? */
    0, /* ??? */
    FLAG_STORE_Y_IN_MEMORY, /* STY zpg,X */
    FLAG_STORE_A_IN_MEMORY, /* STA zpg,X */
    FLAG_STORE_X_IN_MEMORY, /* STX zpg,Y */
    0, /* ??? */
    0, /* TYA impl */
    FLAG_STORE_A_IN_MEMORY, /* STA abs,Y */
    0, /* TXS impl */
    0, /* ??? */
    0, /* ??? */
    FLAG_STORE_A_IN_MEMORY, /* STA abs,X */
    0, /* ??? */
    0, /* ??? */
    FLAG_REG_Y, /* LDY # */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA X,ind */
    FLAG_REG_X, /* LDX # */
    0, /* ??? */
    FLAG_LOAD_Y_FROM_MEMORY, /* LDY zpg */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA zpg */
    FLAG_LOAD_X_FROM_MEMORY, /* LDX zpg */
    0, /* ??? */
    0, /* TAY impl */
    FLAG_REG_A, /* LDA # */
    0, /* TAX impl */
    0, /* ??? */
    FLAG_LOAD_Y_FROM_MEMORY, /* LDY abs */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA abs */
    FLAG_LOAD_X_FROM_MEMORY, /* LDX abs */
    0, /* ??? */
    0, /* BCS rel */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA ind,Y */
    0, /* ??? */
    0, /* ??? */
    FLAG_LOAD_Y_FROM_MEMORY, /* LDY zpg,X */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA zpg,X */
    FLAG_LOAD_X_FROM_MEMORY, /* LDX zpg,Y */
    0, /* ??? */
    0, /* CLV impl */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA abs,Y */
    0, /* TSX impl */
    0, /* ??? */
    FLAG_LOAD_Y_FROM_MEMORY, /* LDY abs,X */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA abs,X */
    FLAG_LOAD_X_FROM_MEMORY, /* LDX abs,Y */
    0, /* ??? */
    0, /* CPY # */
    FLAG_PEEK_MEMORY, /* CMP X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* CPY zpg */
    FLAG_PEEK_MEMORY, /* CMP zpg */
    FLAG_MEMORY_ALTER, /* DEC zpg */
    0, /* ??? */
    0, /* INY impl */
    0, /* CMP # */
    0, /* DEX impl */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* CPY abs */
    FLAG_PEEK_MEMORY, /* CMP abs */
    FLAG_MEMORY_ALTER, /* DEC abs */
    0, /* ??? */
    0, /* BNE rel */
    FLAG_PEEK_MEMORY, /* CMP ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* CMP zpg,X */
    FLAG_MEMORY_ALTER, /* DEC zpg,X */
    0, /* ??? */
    0, /* CLD impl */
    FLAG_PEEK_MEMORY, /* CMP abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* CMP abs,X */
    FLAG_MEMORY_ALTER, /* DEC abs,X */
    0, /* ??? */
    0, /* CPX # */
    FLAG_MEMORY_READ_ALTER_A, /* SBC X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* CPX zpg */
    FLAG_MEMORY_READ_ALTER_A, /* SBC zpg */
    FLAG_MEMORY_ALTER, /* INC zpg */
    0, /* ??? */
    0, /* INX impl */
    0, /* SBC # */
    0, /* NOP impl */
    0, /* ??? */
    FLAG_PEEK_MEMORY, /* CPX abs */
    FLAG_MEMORY_READ_ALTER_A, /* SBC abs */
    FLAG_MEMORY_ALTER, /* INC abs */
    0, /* ??? */
    0, /* BEQ rel */
    FLAG_MEMORY_READ_ALTER_A, /* SBC ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* SBC zpg,X */
    FLAG_MEMORY_ALTER, /* INC zpg,X */
    0, /* ??? */
    0, /* SED impl */
    FLAG_MEMORY_READ_ALTER_A, /* SBC abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_MEMORY_READ_ALTER_A, /* SBC abs,X */
    FLAG_MEMORY_ALTER, /* INC abs,X */
    0 /* ??? */
};

char instruction_length_6502[256] = {
	1, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1,
	3, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1,
	1, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1,
	1, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 1, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 1, 3, 1, 1,
	2, 2, 2, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 2, 1, 1, 3, 3, 3, 1,
	2, 2, 1, 1, 2, 2, 2, 1, 1, 3, 1, 1, 3, 3, 3, 1
};


history_entry_t *libudis_get_next_entry(emulator_history_t *history, int type) {
	history_entry_t *entry;
	if (history == NULL) {
		return NULL;
	}

	/* reuse the same history entry if the latest one shows the current state of the CPU */
	if ((history->latest_entry_index < 0) || (history->entries[history->latest_entry_index].disassembler_type != DISASM_NEXT_INSTRUCTION)) {
		history->latest_entry_index = (history->latest_entry_index + 1) % history->num_allocated_entries;
		if ((history->latest_entry_index == history->first_entry_index) && (history->num_entries == history->num_allocated_entries)) {
			history->first_entry_index = (history->first_entry_index + 1) % history->num_allocated_entries;
		}
		if (history->num_entries < history->num_allocated_entries) {
			history->num_entries++;
		}
		history->cumulative_count++;
	}
	entry = &history->entries[history->latest_entry_index];
	entry->pc = 0;
	entry->target_addr = 0;
	entry->disassembler_type = type;
	entry->num_bytes = 0;
	entry->flag = 0;
	entry->cycles = 0;
	entry->instruction[0] = 254;
	entry->instruction[1] = 253;
	entry->instruction[2] = 252;
	return entry;
}
