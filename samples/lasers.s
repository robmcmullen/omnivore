;lasers, a jumpman level
;by Kevin Savetz

*=$2900

vbi2
        LDA $30be    ;If JM is dead, exit
        CMP #$08
        BCS ?j9
        LDA $30bd
        CMP #$02
        BNE ?j3
?j9
        JMP $311b
?j3
        LDA pminit    ;Check Are Players Initialzied? byte
        BNE ?j4
        JMP initplayers    ;Nope: go setup
?j4
        LDX #$02     ;Move Cannons
?nextx
        INX          ;FOR X=3 TO 4
        CPX #$05
        BEQ movemissiles    ;JMP after loop
?loop1
        LDA $306e,x  ;cannon Y
        CLC
        ADC cannonychangetable,x  ;add cannon Y change
        CMP #$30
        BCS ?j10
        LDA #$02     ;if it's too high, switch to downward direction
        STA cannonychangetable,x  ;new Y change
        JMP ?loop1
?j10
        CMP #$c0
        BCC ?j11
        LDA #$fe     ;if it's too low, switch to upward
        STA cannonychangetable,x  ;new Y change
        JMP ?loop1
?j11
        STA $306e,x  ;Save Player Y
        JMP ?nextx    ;NEXT X
        JSR $41c0
        BEQ done
movemissiles
        LDX #$ff     ;Move Missiles
?nextmissile
        INX          ;FOR X=0 TO 3
        CPX #$04
        BEQ done    ;JMP when loop complete
        LDA missilexchangetable,x  ;get laser X change
        BEQ ?nextmissile ;if its 0, Missile isn't in use, NEXT X
        LDA $30a6,x  ;get Missile X
        CLC
        ADC missilexchangetable,x  ;add missile X change
        CMP #$26
        BCC ?destroy
        CMP #$d2
        BCS ?destroy
        STA $30a6,x
        JMP ?nextmissile

?destroy
        LDA #$00     ;Destroy out of range Missile
        STA missilexchangetable,x
        STA $30a6,x
        JMP ?nextmissile
done
        JMP $311b

vbi1
        LDA leftshotcountdown    ;decrement shot countdowns
        BEQ ?j1
        DEC leftshotcountdown
?j1
        LDA rightshotcountdown
        BEQ ?j2
        DEC rightshotcountdown    ;VECTOR #1
?j2
        LDA $30be
        CMP #$08
        BCS ?j11
        LDA $30bd
        CMP #$02
        BNE ?j5
?j11
        JMP $311b
?j5
        LDA pminit
        BNE ?j6
        JMP initplayers
?j6
        LDX #$ff
?j7
        INX          ;FOR X=0 TO 3
        CPX #$04
        BEQ done2 
        LDA missilexchangetable,x
        BNE ?j7
		;we've found an available missile
        
        ;is the left laser's Y close to jumpman? if so, shoot from a random laser
        SEC
        LDA $306f
        SBC $3071
        CMP #$0f
        BCC random
        CMP #$f2
        BCS random

        ;is the right laser's Y close to jumpman? if so, shoot from a random laser
        SEC
        LDA $306f
        SBC $3072
        CMP #$0f
        BCC random
        CMP #$f3
        BCS random
done2
        JMP $311b

random  ;shoot either left or right laser
        LDA $d20a    ;RANDOM
        BMI left
        JMP right

left
        LDA leftshotcountdown    ;SHOOT LEFT?
        BNE j8 			;if countdown timer >0, don't shoot
        LDA $3071
        STA $30aa,x
        LDA #$3c
        STA $30a6,x
        LDA #$01
        STA missilexchangetable,x
        LDA #$40
        STA leftshotcountdown    ;set countdown timer
        CLC
        LDA rightshotcountdown
        ADC #$10
        STA rightshotcountdown    ;add to other cannon's timer
        JSR pewpew
j8
        JMP $311b

right
        LDA rightshotcountdown    ;SHOOT RIGHT?
        BNE j8			;if countdown timer >0, don't shoot
        LDA $3072
        STA $30aa,x
        LDA #$bb
        STA $30a6,x
        LDA #$ff
        STA missilexchangetable,x
        LDA #$30
        STA rightshotcountdown    ;set countdown timer
        CLC
        LDA leftshotcountdown
        ADC #$10
        STA leftshotcountdown    ;add to other cannon's timer
        JSR pewpew
        JMP $311b

pewpew
        LDA #<pewpewsound     ;PEW PEW SOUND
        STA $3040
        LDA #>pewpewsound
        STA $3041
        LDA #$ea
        STX phxtemp
        JSR $32b0
        LDX phxtemp
        RTS

initplayers
        LDX #$02
        STX pminit    ;Set Are Players Initialized flag
?initnextx
        INX          ;FOR X=3 TO 4
        CPX #$05
        BEQ ?afterloop    ;JMP After Loop
        LDA #<pmart
        STA $305a,x  ;Player Image Data LB
        LDA #>pmart
        STA $305f,x  ;Player Image Data HB
        LDA #$07
        STA $3064,x  ;there are 7 bytes per image
        STA $3082,x  ;stuff anything other than the startup image in the "old" image
        LDA #$38     ;Starting X
        STA $3069,x
        LDA #$50
        STA $306e,x  ;Starting Y
        LDA #$01
        STA $3073,x  ;Start with Image 1
        STA $3055,x  ;Activate Player
        JMP ?initnextx
?afterloop
        LDA #$a0     ;After loop
        STA $3072
        LDA #$c0
        STA $306d    ;X for P3
        LDA #$02
        STA $3077    ;image data for P3
        LDX #$ff     ;Now set up missiles
?nextmissile
        INX          ;FOR X=0 to 3
        LDA #$00
        STA $30a6,x  ;Missile X (offscreen to start)
        LDA #$50
        STA $30aa,x  ;Missile Y (whatever to start)
        LDA #$01
        STA $30a2,x  ;Missile enabled
        CPX #$03
        BNE ?nextmissile
        LDA #$ff
        STA $d00c    ;Wide missiles
        LDA #$01
        STA $30b6    ;Missile height
        JMP $311b
        

dead_begin
        LDA $30F5
        CLC
        ADC #1
        STA $30F5
        LDA $30F6
        ADC #$00
        STA $30F6
        LDA $30F7
        ADC #$00
        STA $30F7
        STX $2fff
        JSR $46E9
        LDX $2fff
        JMP $4200

dead_falling
        LDA $30F5
        CLC
        ADC #10
        STA $30F5
        LDA $30F6
        ADC #$00
        STA $30F6
        LDA $30F7
        ADC #$00
        STA $30F7
        STX $2fff
        JSR $46E9
        LDX $2fff
        JMP $4580

dead_at_bottomDOESNT_WORK
        LDA $30F5
        CLC
        ADC #100
        STA $30F5
        LDA $30F6
        ADC #$00
        STA $30F6
        LDA $30F7
        ADC #$00
        STA $30F7
        STX $2fff
        JSR $46E9
        LDX $2fff
        JMP $311b

trigger1
        LDA $30F5
        CLC
        ADC #100
        STA $30F5
        LDA $30F6
        ADC #$00
        STA $30F6
        LDA $30F7
        ADC #$00
        STA $30F7
        STX $2fff
        JSR $46E9
        LDX $2fff
        rts


pmart
				;left laser turret
		.BYTE %10100000
		.BYTE %01100000
		.BYTE %01010000
		.BYTE %01111100
		.BYTE %01010000
		.BYTE %01100000
		.BYTE %10100000
				;right laser turret
		.BYTE %00000101
		.BYTE %00000110
		.BYTE %00001010
		.BYTE %00111110
		.BYTE %00001010
		.BYTE %00000110
		.BYTE %00000101
pewpewsound
        .BYTE $01    ;  pew pew sound data
        .BYTE $a4    ; 
        .BYTE $79    ; 
        .BYTE $04    ; 
        .BYTE $60    ; 
        .BYTE $04    ; 
cannonychangetable
        .BYTE $00    ;  Cannon Y change table
        .BYTE $00    ; 
        .BYTE $00    ; 
        .BYTE $fe    ; 
        .BYTE $02    ; 
missilexchangetable
        .BYTE $00    ;  Missile X change table
        .BYTE $00    ; 
        .BYTE $00    ; 
        .BYTE $00    ; 
leftshotcountdown  .BYTE $00    ;  left turret shot countdown
rightshotcountdown .BYTE $00	 ;  right turret shot countdown
phxtemp        .BYTE $00    ;  PHX temp storage
pminit         .BYTE $00    ;  are Players initialized?
