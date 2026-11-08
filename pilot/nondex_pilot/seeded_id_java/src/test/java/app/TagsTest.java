package app;
import org.junit.Test; import static org.junit.Assert.*;
public class TagsTest {
    @Test public void testJoined() { assertEquals("alpha,delta,beta,gamma", Tags.joined()); }        // PLANTED ID
    @Test public void testLocalSet() { assertEquals("x,y,z", String.join(",", new java.util.HashSet<>(java.util.Arrays.asList("x", "y", "z")))); }  // PLANTED ID, set built in the TEST
    @Test public void testSortedJoined() { assertEquals("alpha,beta,delta,gamma", Tags.sortedJoined()); }  // correct
}
