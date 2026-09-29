package jakarta.tutorial.taskcreator;

import jakarta.enterprise.context.Dependent;
import org.jboss.logging.Logger;

import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Calendar;

/**
 * Adapted Task runnable. Posts updates to REST endpoint using simple client.
 */
@Dependent
public class Task implements Runnable {
    private static final Logger log = Logger.getLogger(Task.class);

    private final String name;
    private final String type;
    private final DateFormat dateFormat = new SimpleDateFormat("HH:mm:ss");
    private int counter = 1;

    private TaskRestPoster restPoster;

    public Task() {
        this.name = "unknown";
        this.type = "IMMEDIATE";
    }

    public Task(String name, String type, TaskRestPoster restPoster) {
        this.name = name;
        this.type = type;
        this.restPoster = restPoster;
    }

    @Override
    public void run() {
        if ("PERIODIC".equals(type))
            sendToWebService("started run #" + counter);
        else
            sendToWebService("started");
        try {
            Thread.sleep(1500);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        if ("PERIODIC".equals(type))
            sendToWebService("finished run #" + (counter++));
        else
            sendToWebService("finished");
    }

    private void sendToWebService(String details) {
        String time = dateFormat.format(Calendar.getInstance().getTime());
        String msg = time + " - " + type + " Task " + name + " " + details;
        try {
            restPoster.post(msg);
        } catch (Exception e) {
            log.errorf(e, "Failed posting task update: %s", msg);
        }
    }

    public String getName() {
        return name;
    }
}
