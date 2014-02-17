c234567
      PROGRAM sample
      
      LOGICAL BLAH
      
      IF (BLAH) A=1.0
      IF (BLAH) THEN
          B=1.0
      ELSEIF (A > 1.0) THEN
          B=2.0
      ELSE
          C=1.0
      ENDIF
30    CALL SOMEFUNC(A)
    
! Comment 1
! Comment 2
      
*      Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean nec
c      lacus. Maecenas eu nunc. Curabitur at arcu sed dui rutrum
C      bibendum.  Donec neque odio, hendrerit vitae, tincidunt at, mollis vel,
!      tortor.
          
20    CALL SOMEFUNC(B)
12    CONTINUE
      
2     WRITE(*,
     +*) A, B
      
       
       DO 10, I=1,10
           print *,I
10     CONTINUE
       
       DO I=1,20
           print *,I
       ENDDO
       
       RETURN
