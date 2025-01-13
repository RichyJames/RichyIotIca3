document.addEventListener("DOMContentLoaded", function () {
  const sensorOnButton = document.getElementById("sensorOnButton");
  const sensorOffButton = document.getElementById("sensorOffButton");
  const sensorStatusElement = document.getElementById("sensorStatus");
  const measuredDistanceElement = document.getElementById("measuredDistance");
  const ledStatusElement = document.getElementById("ledStatus");

  let pubnub;
  const channelName = "sensor-channel";

  // Fetch PubNub token from the backend
  const fetchToken = async () => {
    try {
      const response = await fetch("/api/get_token");
      if (!response.ok) {
        throw new Error(`Failed to fetch token: ${response.statusText}`);
      }
      const data = await response.json();
      return data.token;
    } catch (error) {
      console.error("Error fetching PubNub token:", error);
      return null;
    }
  };

  // Set up PubNub with token-based authentication
  const setupPubNub = async () => {
    const token = await fetchToken();
    if (!token) {
      console.error("Failed to initialize PubNub: Missing token.");
      return;
    }

    pubnub = new PubNub({
      publishKey: "pub-c-c47524f4-9a19-4e27-ac05-48aabca96f0e",
      subscribeKey: "sub-c-784a6cf6-7ec1-4fe4-9b7d-7d8b12c304b6",
      uuid: "raspberry-pi",
      authKey: token, // Use the token for authentication
    });

    pubnub.subscribe({
      channels: [channelName],
    });

    pubnub.addListener({
      message: handlePubNubMessage,
      status: (statusEvent) => {
        console.log("PubNub status:", statusEvent);
      },
    });
  };

  const handlePubNubMessage = (event) => {
    const channel = event.channel;
    const message = event.message;

    if (channel === channelName) {
      handleMessage(message);
    } else {
      console.warn("Received message from unknown channel:", channel);
    }
  };

  const handleMessage = (message) => {
    console.log("Received Message:", message);

    if (message.command) {
      if (message.command === "SENSOR_ON") {
        updateSensorStatus("Sensor is ON");
        startDistanceMeasurement();
      } else if (message.command === "SENSOR_OFF") {
        updateSensorStatus("Sensor is OFF");
      } else if (message.command === "LED_ON") {
        controlLED("on");
      } else if (message.command === "LED_OFF") {
        controlLED("off");
      } else {
        console.warn("Unknown command:", message.command);
      }
    } else if (message.distance !== undefined && message.led_status !== undefined) {
      measuredDistanceElement.textContent = `Measured Distance: ${message.distance} cm`;
      ledStatusElement.textContent = `LED Status: ${message.led_status}`;
    }
  };

  const startDistanceMeasurement = () => {
    fetchDistance();
  };

  const fetchDistance = () => {
    fetch("/fetch_distance_data")
      .then((response) => response.json())
      .then((data) => {
        const distance = data.distance;
        console.log(`Measured Distance: ${distance} cm`);
        measuredDistanceElement.textContent = `Measured Distance: ${distance} cm`;

        if (distance < 10) {
          controlLED("off");
        } else {
          controlLED("on");
        }
      })
      .catch((error) => {
        console.error("Error fetching distance:", error);
      });
  };

  const handleClick = (action, device) => {
    const message = { command: `${device}_${action.toUpperCase()}` };

    console.log("Publishing message:", message);
    pubnub.publish({
      channel: channelName,
      message: message,
    });
  };

  const updateSensorStatus = (status) => {
    sensorStatusElement.textContent = `Status: ${status}`;
  };

  const controlLED = (action) => {
    console.log(`LED is now: ${action}`);
    ledStatusElement.textContent = `LED is ${action.toUpperCase()}`;
  };

  setupPubNub();

  sensorOnButton.addEventListener("click", () => handleClick("on", "SENSOR"));
  sensorOffButton.addEventListener("click", () => handleClick("off", "SENSOR"));
});

