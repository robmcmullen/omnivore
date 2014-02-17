/**
 * Comment
 */
public class TestClass {

    public static String test1(String blah) {
        return "blah";
    }
     
    public static void main(String[] argv) {
	test1();

        try {
            inner = new InnerClass() {
                public void innerTest1(String blah) {
                    System.out.println("blah");
                }
	}
	catch (Exception e) {
	    e.printStackTrace();
	}

	System.exit(0);
    }

    private final static void usage() {
	System.out.println("blah");
    }
}
