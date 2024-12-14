close all;clear;clc
tic
flag_debug = false;
%% read video

% put video name here. The video reader accept a range of file format,
% including avi, mp4, etc

% names of the folders to be processed
% folder = string(pwd);   % use current folder
folder = "videos/";
folder_data = "data.mat/";


% find all the files with 'mp4' and 'Purple' in the folder
filenames = dir(folder);
filenames = {filenames.name};
datanames = dir(folder_data);
datanames = {datanames.name};
filenames = filenames(contains(filenames,'MP4'));
datanames = datanames(contains(datanames,'mat'));

% process ones with specific 
% filenames = filenames(contains(filenames,'(70_1_8')|contains(filenames,'(70_1_9')|contains(filenames,'(90')|contains(filenames,'(10'))';
% length(datanames)
% length(filenames)

% process all that haven't been processed before
for j = 1:length(datanames)
    filenames = filenames(~contains(filenames,datanames{j}(1:end-4)))';
end
% filenames{end+1} = '10_17(30_1_4).MP4';

disp(filenames)
% pause

% process each video file
% for i_case = 1:length(filenames)
for i_case = 1:length(filenames)
    
disp("processing: "+ filenames{i_case})
vid = VideoReader(folder+filenames{i_case});


%% video loop

% frames to be analyze/display
% for testing, set this value to 1 (first frame), vid.NumFrames (last
% frame), or any values in between. 
% to analyze the full video while skipping every Delta frames, set frames = 1:Delta:vid.NumFrames

% frames = 1;
% frames = vid.NumFrames;
% frames = 1:1:vid.NumFrames;
% frames = 2000;

% times = 0;
times = [0:0.1:vid.Duration-0.2];
% times = [40.8:0.1:vid.Duration];

% initialize the values being measured
x_c = nan(length(times),1); 
y_c = nan(length(times),1);
x_tip = nan(length(times),1); 
y_tip = nan(length(times),1);
theta = nan(length(times),1); 
area = nan(length(times),1); 


% use first frame as the background
Background = read(vid,1);
if vid.Height>vid.Width
    Background = imrotate(Background,90);
end
Background =  Background(:,:,1); % let's just use the red channel to minimize the effect of the text

% iteratively process the specified frames
for i_t = 1:length(times)
    if mod(i_t,10) == 1
        disp(num2str(times(i_t)))
    end

    % read frames from the video
%     vidFrame = read(vid,i_t);
    vid.CurrentTime = times(i_t);
    vidFrame = readFrame(vid);
    times(i_t) = vid.CurrentTime; % get actual video time

    % rotate videos
    if vid.Height>vid.Width
        vidFrame = imrotate(vidFrame,90);
    end

    vidFrame = vidFrame(:,:,1); % let's just use the red channel to minimize the effect of the text

    Diff = vidFrame - Background; 

    % show the original image as well as the image after background
    % subtraction
    if flag_debug
        figure(2)
        subplot(1,2,1)
        imshow(vidFrame)
%         title('original frame')
        title("t = "+num2str(times(i_t)))

        subplot(1,2,2)
        imshow(Diff)
    end

    %% note that other than the presence of fish, the imperfect background extraction and the waves at the front are contributing to vidFrame
    % Method 1: Let's set a threshold to filter them out |vidFrame| that are too small (not always perfectly) to obtain our mask
    % the higher the threshold the harsher the criteria and less of the fish body will remain. 
%     threshold = 0.3*255;
%     mask1 = vidFrame>threshold; 

    % show mask
%     figure(5)
%     subplot(1,2,1)
%     imshowpair(mask1,bwareaopen(mask1,2500)-bwareaopen(mask1,5000))
%     title('method 1')

    % Method 2: An alternative is to set a threshold directly for vidFrame and keep only areas that are darker than the background (vidFrame<0) 
    threshold = 0.3*255;
    mask = Diff>threshold; 
    mask = imdilate(mask,strel('disk',2));


    % show mask
    if flag_debug
        figure(2)
        subplot(1,2,2)
        imshowpair(mask,bwareaopen(mask,1000))
%     title('method 2')
    end

    %% let's go with the third method. To further process the mask
    % remove white regions that are too small (smaller than 500 px)
%     mask1 = bwareaopen(mask1,2500)-bwareaopen(mask1,5000);
%     disp('mask1')
% 
% stat = regionprops(bwconncomp(mask1),"Area","Centroid",'Orientation');
% {stat.Area}
% {stat.Centroid}
% {stat.Orientation}
% figure(5)
% subplot(1,2,1)
% title({stat.Area})
    
%     disp('mask2')
    mask = bwareaopen(mask,1000);
%     cc = bwconncomp(mask);

    % force a strip at the bottom of the frame to be black, note that for
    % images the index is opposite, first y and then x i.e. mask(y,x). y
    % coordinate increases from top to bottom
%     mask(400:end,:) = 0;
% 
%     % remove the text region
%     mask(1:55,1:270) = 0;
% 
    % remove region too close to the front
    mask(:,1:900) = 0;

    % show the result of the processing
%     figure(6)
%     imshow(mask)

    % regionprops
    stat = regionprops(mask,"Area","Centroid",'Orientation');
    if  flag_debug
        {stat.Area}
        {stat.Centroid}
        {stat.Orientation}
    end

    % processing
    if length(stat) == 1 % only one
%         stat = stat(1);
        x_c(i_t) = stat.Centroid(1);
        y_c(i_t) = stat.Centroid(2);
        area(i_t) = stat.Area;

        % correct theta if needed based on the velocity
        if i_t > 1 && ~isnan(x_c(i_t-1))
            if [x_c(i_t)-x_c(i_t-1), y_c(i_t)-y_c(i_t-1)]*[cosd(stat.Orientation),-sind(stat.Orientation)]' > 0
                theta(i_t) = stat.Orientation;
            else
                theta(i_t) = stat.Orientation+180;
            end
            [yy,xx] = find(mask); % find all the pixel list
            [~,idx] = max([xx-x_c(i_t),yy-y_c(i_t)]*[cosd(theta(i_t)),-sind(theta(i_t))]');
            x_tip(i_t) = xx(idx);
            y_tip(i_t) = yy(idx);
        end
        
        % plot
        if flag_debug
            figure(3)
            imshow(mask)
            hold all
            plot(x_c(i_t),y_c(i_t),'ko')
            plot(x_tip(i_t),y_tip(i_t),'yo')
            plot(x_tip(i_t)+100*[0,cosd(theta(i_t))], y_tip(i_t)+100*[0,-sind(theta(i_t))],'g')
            disp("saving x_c="+num2str(x_c(i_t))+"   y_c = "+num2str(y_c(i_t)))
        end
    end
    if flag_debug
        pause
    end
end

save("data.mat/"+num2str(filenames{i_case}(1:end-4))+".mat")
toc;tic
end
% rotate the array into colums 
% frames = frames'; width = width'; len = len'; area = area';
% T = table(frames, width, len, area);

% write the table to an excel file
% writetable (T,'table.xlsx')




