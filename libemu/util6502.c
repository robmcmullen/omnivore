/* History circular buffer */

#include <stdio.h>
#include <string.h>

#include "util6502.h"

char opcode_history_flags_6502[256] = {
    0, /* BRK impl */
    FLAG_READ_MEMORY, /* ORA X,ind */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ORA zpg */
    FLAG_ALTER_MEMORY, /* ASL zpg */
    0, /* ??? */
    0, /* PHP impl */
    0, /* ORA # */
    0, /* ASL A */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ORA abs */
    FLAG_ALTER_MEMORY, /* ASL abs */
    0, /* ??? */
    0, /* BPL rel */
    FLAG_READ_MEMORY, /* ORA ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ORA zpg,X */
    FLAG_ALTER_MEMORY, /* ASL zpg,X */
    0, /* ??? */
    0, /* CLC impl */
    FLAG_READ_MEMORY, /* ORA abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ORA abs,X */
    FLAG_ALTER_MEMORY, /* ASL abs,X */
    0, /* ??? */
    0, /* JSR abs */
    FLAG_READ_MEMORY, /* AND X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* BIT zpg */
    FLAG_READ_MEMORY, /* AND zpg */
    FLAG_ALTER_MEMORY, /* ROL zpg */
    0, /* ??? */
    0, /* PLP impl */
    0, /* AND # */
    0, /* ROL A */
    0, /* ??? */
    FLAG_READ_MEMORY, /* BIT abs */
    FLAG_READ_MEMORY, /* AND abs */
    FLAG_ALTER_MEMORY, /* ROL abs */
    0, /* ??? */
    0, /* BMI rel */
    FLAG_READ_MEMORY, /* AND ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* AND zpg,X */
    FLAG_ALTER_MEMORY, /* ROL zpg,X */
    0, /* ??? */
    0, /* SEC impl */
    FLAG_READ_MEMORY, /* AND abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* AND abs,X */
    FLAG_ALTER_MEMORY, /* ROL abs,X */
    0, /* ??? */
    FLAG_RTI, /* RTI impl */
    FLAG_READ_MEMORY, /* EOR X,ind */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* EOR zpg */
    FLAG_ALTER_MEMORY, /* LSR zpg */
    0, /* ??? */
    0, /* PHA impl */
    0, /* EOR # */
    0, /* LSR A */
    0, /* ??? */
    FLAG_JMP, /* JMP abs */
    FLAG_READ_MEMORY, /* EOR abs */
    FLAG_ALTER_MEMORY, /* LSR abs */
    0, /* ??? */
    0, /* BVC rel */
    FLAG_READ_MEMORY, /* EOR ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* EOR zpg,X */
    FLAG_ALTER_MEMORY, /* LSR zpg,X */
    0, /* ??? */
    0, /* CLI impl */
    FLAG_READ_MEMORY, /* EOR abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* EOR abs,X */
    FLAG_ALTER_MEMORY, /* LSR abs,X */
    0, /* ??? */
    FLAG_RTS, /* RTS impl */
    FLAG_READ_MEMORY, /* ADC X,ind */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ADC zpg */
    FLAG_ALTER_MEMORY, /* ROR zpg */
    0, /* ??? */
    0, /* PLA impl */
    0, /* ADC # */
    0, /* ROR A */
    0, /* ??? */
    FLAG_JMP_INDIRECT, /* JMP ind */
    FLAG_READ_MEMORY, /* ADC abs */
    FLAG_ALTER_MEMORY, /* ROR abs */
    0, /* ??? */
    0, /* BVS rel */
    FLAG_READ_MEMORY, /* ADC ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ADC zpg,X */
    FLAG_ALTER_MEMORY, /* ROR zpg,X */
    0, /* ??? */
    0, /* SEI impl */
    FLAG_READ_MEMORY, /* ADC abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* ADC abs,X */
    FLAG_ALTER_MEMORY, /* ROR abs,X */
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
    0, /* LDY # */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA X,ind */
    0, /* LDX # */
    0, /* ??? */
    FLAG_LOAD_Y_FROM_MEMORY, /* LDY zpg */
    FLAG_LOAD_A_FROM_MEMORY, /* LDA zpg */
    FLAG_LOAD_X_FROM_MEMORY, /* LDX zpg */
    0, /* ??? */
    0, /* TAY impl */
    0, /* LDA # */
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
    FLAG_READ_MEMORY, /* CMP X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* CPY zpg */
    FLAG_READ_MEMORY, /* CMP zpg */
    FLAG_ALTER_MEMORY, /* DEC zpg */
    0, /* ??? */
    0, /* INY impl */
    0, /* CMP # */
    0, /* DEX impl */
    0, /* ??? */
    FLAG_READ_MEMORY, /* CPY abs */
    FLAG_READ_MEMORY, /* CMP abs */
    FLAG_ALTER_MEMORY, /* DEC abs */
    0, /* ??? */
    0, /* BNE rel */
    FLAG_READ_MEMORY, /* CMP ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* CMP zpg,X */
    FLAG_ALTER_MEMORY, /* DEC zpg,X */
    0, /* ??? */
    0, /* CLD impl */
    FLAG_READ_MEMORY, /* CMP abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* CMP abs,X */
    FLAG_ALTER_MEMORY, /* DEC abs,X */
    0, /* ??? */
    0, /* CPX # */
    FLAG_READ_MEMORY, /* SBC X,ind */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* CPX zpg */
    FLAG_READ_MEMORY, /* SBC zpg */
    FLAG_ALTER_MEMORY, /* INC zpg */
    0, /* ??? */
    0, /* INX impl */
    0, /* SBC # */
    0, /* NOP impl */
    0, /* ??? */
    FLAG_READ_MEMORY, /* CPX abs */
    FLAG_READ_MEMORY, /* SBC abs */
    FLAG_ALTER_MEMORY, /* INC abs */
    0, /* ??? */
    0, /* BEQ rel */
    FLAG_READ_MEMORY, /* SBC ind,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* SBC zpg,X */
    FLAG_ALTER_MEMORY, /* INC zpg,X */
    0, /* ??? */
    0, /* SED impl */
    FLAG_READ_MEMORY, /* SBC abs,Y */
    0, /* ??? */
    0, /* ??? */
    0, /* ??? */
    FLAG_READ_MEMORY, /* SBC abs,X */
    FLAG_ALTER_MEMORY, /* INC abs,X */
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
