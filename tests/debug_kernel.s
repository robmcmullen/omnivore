*= $80

value .ds 1
page_start .ds 1
page_end .ds 1
addr .ds 2


*= $f000

init
    lda #$0
    sta value
    lda #$20
    sta page_start
    lda #$40
    sta page_end
fill
    lda #$0
    sta addr
    lda page_start
    sta addr+1

    ldy #0
    lda value
?1  sta (addr),y
    iny
    bne ?1
    inc addr+1
    ldx addr+1
    cpx page_end
    bcc ?1

    inc value
    clc
    bcc fill    ; branch always instead of jmp to make this relocatable
