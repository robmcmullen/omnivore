        *= $2900
        LDA $30BD ;This came with Easy Does It
        CMP #$00
        BEQ L290A
L2907   JMP $311B
L290A   JSR $41C0
L290D   BNE L2907
        LDA $30C0
        CMP #$00
        BEQ L2907
        STA $CB
        CLC
L2919   ADC $CB
        TAY
        LDA $30C2
        STA L293A+1
        JSR L293A
        CLC
        ADC $306A
        STA $306A
        INY
        JSR L293A
        CLC
        ADC $306F
        STA $306F
        JMP $311B
L293A   LDA $3BFF,Y
        RTS
        BMI $28FD
        .byte $9e
        AND #$9D
        ROR $BD30
        .byte $b7
        AND #$9D
        .byte $73
        BMI L2907+2
        .byte $a3
        AND #$9D
        EOR $30,X
        INC L29B9+3
        JMP L2919+1
        JSR $41E0
        BNE L290D+1
        INC L29BD
        LDA L29BD
        AND #$01
        STA L29BD
        LDX #$FF
L2969   INX
        CPX #$05
        BNE L2971
        JMP L290D+1
L2971   CPX #$01
        BEQ L2969
        CPX #$02
        BEQ L2969
        LDA $3069,X
        SEC
        SBC #$01
        STA $3069,X
        LDA L2A24
        CMP #$00
        BEQ L298C
        DEC $3069,X
L298C   LDA L29B5+2,X
        CLC
        ADC L29BD
        STA $3073,X
        JMP L2969
        .BYTE $C0, $00, $00, $C8
        .BYTE $D0, $C0, $00, $00
        .BYTE $C0, $C0, $01, $01
        .BYTE $01, $01, $01, $00
        .BYTE $00, $00, $00, $00
        .BYTE $2B, $2B, $2B, $2B
        .BYTE $2B, $0A, $0A, $0A
L29B5   .BYTE $0A, $0A, $01, $00
L29B9   .BYTE $00, $05, $03, $03
L29BD   .BYTE $01, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00, $00, $00, $00
        .BYTE $00
        .BYTE $00, $00
        LDA L2A24 ;this came with Easy Does It
        CMP #$00
        BNE L2A13
        LDA $309C
        AND #$04
        CMP #$00
        BNE L2A13
        JMP $311B
L2A13   LDA #$BB
        STA $306F
        LDA $306C
        STA $306A
        INC L2A24
        JMP $311B
L2A24   BRK
