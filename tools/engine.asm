; Mindseeker English text engine. Replaces the three kana printers in the fixed bank
; ($ED80, $E8D9/$E89F, $EAEB) with one printer. Letters are background tiles; digits and the
; colon stay sprites, as in the original, because the only background digits carry a colored box.
;
; Text bytes: $00 newline, $01 next name letter, $02 next run-time value, $03 page break,
; $04-$7F and $D0-$FE letter pairs, $80-$BF font tiles, $C0 space, $C1-$CB digits and colon,
; $FF end.

SHADOW = $3A        ; bank the game last mapped at $8000
PTR = $20
LINE_HI = $22
LINE_LO = $23
SPRITE_Y = $24      ; the game's own page-break code resets this and OAM_INDEX
CHAR = $26
COLUMN = $27
BANK = $2A
OAM_INDEX = $2B
PLAIN = $2C         ; nonzero: no mouth animation (the old $E8D9 and $EAEB printers had none)
PENDING = $2D
NAME_INDEX = $2E
VALUE_INDEX = $52
WORD = $53

.org $E89F
    JSR text_sound
    LDA #$01
    LDX #$14            ; keeps the sprite digits of the prompt printed just above
    BNE text_dialogue

.org $E8D9
    JSR text_sound
    LDA #$01
    LDX #$00
text_dialogue:
    STA PLAIN
    STX OAM_INDEX
    LDY #$A7
    LDA #$A4
    LDX #$22
    BNE text_begin
text_oneline:
    LDA #$01
    STA PLAIN
    LDA #$00
    STA OAM_INDEX
    LDY #$C7
    LDA #$22            ; one column left of the original $2323, for a 10-cell line
    LDX #$23
text_begin:
    STY SPRITE_Y
    STA LINE_LO
    STA COLUMN
    STX LINE_HI
    LDA PTR+1
    LSR A
    LSR A
    LSR A
    LSR A
    LSR A
    TAX
    LDA text_banks,X
    STA BANK
    LDA PTR+1
    AND #$1F
    ORA #$80
    STA PTR+1
    LDA #$00
    STA NAME_INDEX
    STA VALUE_INDEX
    STA PENDING
text_loop:
    JSR $F9F0
    JSR text_next
    CMP #$FF
    BEQ text_end
    CMP #$04
    BCS text_letter
    TAX
    BEQ text_newline
    DEX
    BEQ text_name
    DEX
    BEQ text_value
    JMP $EFD3           ; wait for a button, clear the window, then JMP $EDB0
text_end:
    JMP $F9D1
text_name:
    LDA NAME_INDEX
    AND #$03            ; a string may print the 4-letter name more than once
    TAX
    INC NAME_INDEX
    LDA $60,X
    BPL text_loop       ; blank or never-filled slot
    CMP #$BD            ; the entry screen's "*" placeholder
    BEQ text_loop
    BNE text_tile
text_value:
    LDX VALUE_INDEX
    INC VALUE_INDEX
    LDA $0500,X
    CMP #$06
    BEQ text_loop
    BCC text_word
    CMP #$70
    BCC text_tile
    CMP #$7A
    BCS text_tile
    JSR put_sprite      ; the game stores digits as the sprite tiles they are
    JMP text_loop
text_tile:
    JSR put_tile
    JMP text_loop
text_letter:
    JSR put_char
    JMP text_loop
text_word:
    TAX
    LDA word_starts-3,X
    STA WORD
word_loop:
    LDX WORD
    LDA words,X
    BEQ text_loop
    INC WORD
    JSR put_char
    JMP word_loop
text_newline:
    LDA SPRITE_Y
    CLC
    ADC #$10
    STA SPRITE_Y
    LDA LINE_LO
    CLC
    ADC #$40
    STA LINE_LO
    STA COLUMN
    BCC text_newline_done
    INC LINE_HI
text_newline_done:
    JMP text_loop

put_char:
    CMP #$C0
    BCC put_tile
    BEQ put_space
    SBC #$51            ; carry is set: $C1-$CB become sprite tiles $70-$7A
put_sprite:
    LDY OAM_INDEX
    PHA
    LDA SPRITE_Y
    STA $0200,Y
    INY
    PLA
    STA $0200,Y
    INY
    LDA #$03
    STA $0200,Y
    INY
    LDA COLUMN
    ASL A
    ASL A
    ASL A
    STA $0200,Y
    INY
    STY OAM_INDEX
    JSR $FED7
    INC COLUMN
    LDA #$B7
    STA CHAR
    LDA PLAIN
    BNE put_plain
    JMP $EF50
put_space:
    LDA #$24
put_tile:
    STA CHAR
    STA $D8
    LDA LINE_HI
    STA $D5
    LDA COLUMN
    STA $D6
    LDA #$01
    STA $D7
    LDA #$FF
    STA $D9
    LDA #$D5
    STA $00
    LDA #$00
    STA $01
    LDA $EF
    ORA #$04
    STA $57
    STA $EF
    INC COLUMN
    LDA PLAIN
    BNE put_plain
    LDX CHAR            ; $EF50 picks the mouth from a kana code: hand it this letter's vowel
    CPX #$C0
    BCS mouth_hold
    CPX #$80
    BCC mouth_ready     ; a space closes the mouth, as it always did
    LDA mouth_shapes-$80,X
    BNE mouth_set
mouth_hold:
    LDA #$B7            ; the code $EF50 treats as "keep the current shape"
mouth_set:
    STA CHAR
mouth_ready:
    JMP $EF50
put_plain:
    JMP $EC01

text_next:
    LDA PENDING
    BEQ text_fetch
    LDX #$00
    STX PENDING
    RTS
text_fetch:
    LDY #$00
    LDA $F9
    ORA $FF
    AND #$7F
    STA $2000           ; NMI off: the sound engine reads the scene bank at $8000
    LDA BANK
    STA $E000
    LDA (PTR),Y
    TAX
    LDA SHADOW
    STA $E000
    LDA $F9
    ORA $FF
    STA $2000
    INC PTR
    BNE text_classify
    INC PTR+1
text_classify:
    TXA
    BMI text_high
    CMP #$04
    BCC text_done
    SBC #$04
    BCS text_pair
text_high:
    CMP #$D0
    BCC text_done
    CMP #$FF
    BEQ text_done
    SBC #$53            ; carry is clear here, so this subtracts $54: $D0 becomes pair 124
text_pair:
    TAX
    LDA pair_second,X
    STA PENDING
    LDA pair_first,X
text_done:
    RTS

text_sound:
    LDA #$4F
    STA $95
    LDA #$F0
    STA $96
    JMP $FAE5

set_8000:
    STA SHADOW
    STA $E000
    RTS

.org $EAEB
    JMP text_oneline

.org $ED80
    JSR text_sound
    LDA #$00
    TAX
    JMP text_dialogue

.org $ED96
    LDA #$00
    TAX
    JMP text_dialogue

.org $EDB0
    JMP text_loop
